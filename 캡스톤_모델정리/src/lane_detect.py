#!/usr/bin/env python3
"""
UNet 기반 차선 분할 모델과 학습/추론 유틸리티.
"""

from __future__ import annotations

import argparse
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence, Tuple

import numpy as np
from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_DIR = PROJECT_ROOT / "dataset" / "lane"
MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "lane_detect.pt"
DEFAULT_OUTPUT_MASK = PROJECT_ROOT / "outputs" / "lane_mask.png"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

__all__ = [
    "DoubleConv",
    "Down",
    "Up",
    "OutConv",
    "UNet",
    "DiceLoss",
    "CombinedLoss",
    "LaneSegDataset",
    "TrainConfig",
    "count_parameters",
    "seed_everything",
    "load_lane_pairs",
    "create_dataloaders",
    "train_cli",
    "predict_cli",
    "main",
]


@dataclass
class TrainConfig:
    image_size: Tuple[int, int] = (256, 256)
    epochs: int = 50
    batch_size: int = 8
    lr: float = 1e-4
    weight_decay: float = 1e-5
    val_split: float = 0.2
    num_workers: int = 4
    seed: int = 42
    bce_weight: float = 0.5
    dice_weight: float = 0.5


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class LaneSegDataset(Dataset):
    """이미지/마스크 페어를 로드해 텐서로 반환하는 데이터셋."""

    def __init__(self, image_paths: Sequence[Path], mask_paths: Sequence[Path], image_size: Tuple[int, int]):
        if len(image_paths) != len(mask_paths):
            raise ValueError("이미지와 마스크 개수가 다릅니다.")
        self.pairs = list(zip(image_paths, mask_paths))
        self.image_size = image_size

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        image_path, mask_path = self.pairs[idx]
        image = Image.open(image_path).convert("RGB")
        mask = Image.open(mask_path).convert("L")

        if image.size != self.image_size:
            image = image.resize(self.image_size, Image.BILINEAR)
        if mask.size != self.image_size:
            mask = mask.resize(self.image_size, Image.NEAREST)

        image_arr = np.asarray(image, dtype=np.float32) / 255.0
        image_tensor = torch.from_numpy(image_arr.transpose(2, 0, 1))

        mask_arr = np.asarray(mask, dtype=np.float32) / 255.0
        mask_tensor = torch.from_numpy(mask_arr).unsqueeze(0)

        return image_tensor, mask_tensor


def load_lane_pairs(dataset_dir: Path) -> tuple[list[Path], list[Path]]:
    image_dir = dataset_dir / "images"
    mask_dir = dataset_dir / "masks"

    if not image_dir.exists():
        raise FileNotFoundError(f"이미지 디렉터리를 찾을 수 없습니다: {image_dir}")
    if not mask_dir.exists():
        raise FileNotFoundError(f"마스크 디렉터리를 찾을 수 없습니다: {mask_dir}")

    image_paths = sorted(p for p in image_dir.glob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)
    if not image_paths:
        raise FileNotFoundError(f"{image_dir} 에서 지원하는 이미지 확장자를 찾을 수 없습니다.")

    mask_map = {p.stem: p for p in mask_dir.glob("*") if p.suffix.lower() in IMAGE_EXTENSIONS}
    missing = [p.name for p in image_paths if p.stem not in mask_map]
    if missing:
        sample = ", ".join(missing[:5])
        raise FileNotFoundError(f"다음 이미지에 해당하는 마스크를 찾지 못했습니다: {sample}")

    masks = [mask_map[p.stem] for p in image_paths]
    return image_paths, masks


def create_dataloaders(
    image_paths: Sequence[Path],
    mask_paths: Sequence[Path],
    config: TrainConfig,
) -> tuple[DataLoader, DataLoader]:
    if not 0.0 < config.val_split < 1.0:
        raise ValueError("val_split 값은 0과 1 사이여야 합니다.")

    train_images, val_images, train_masks, val_masks = train_test_split(
        image_paths,
        mask_paths,
        test_size=config.val_split,
        random_state=config.seed,
        shuffle=True,
    )

    train_dataset = LaneSegDataset(train_images, train_masks, config.image_size)
    val_dataset = LaneSegDataset(val_images, val_masks, config.image_size)

    pin_memory = torch.cuda.is_available()
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        pin_memory=pin_memory,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=pin_memory,
    )
    return train_loader, val_loader


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class DoubleConv(nn.Module):
    """(conv → BN → ReLU) × 2 블록."""

    def __init__(self, in_channels: int, out_channels: int, mid_channels: int | None = None):
        super().__init__()
        if mid_channels is None:
            mid_channels = out_channels
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(mid_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.double_conv(x)


class Down(nn.Module):
    """MaxPool → DoubleConv 블록."""

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.maxpool_conv = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(in_channels, out_channels),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.maxpool_conv(x)


class Up(nn.Module):
    """Upsample → concat skip → DoubleConv."""

    def __init__(self, in_channels: int, out_channels: int, bilinear: bool = True):
        super().__init__()
        if bilinear:
            self.up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=True)
            self.conv = DoubleConv(in_channels, out_channels, in_channels // 2)
        else:
            self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
            self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor:
        x1 = self.up(x1)
        diff_y = x2.size(2) - x1.size(2)
        diff_x = x2.size(3) - x1.size(3)
        x1 = F.pad(x1, [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2])
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class OutConv(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)


class UNet(nn.Module):
    def __init__(self, n_channels: int = 3, n_classes: int = 1, bilinear: bool = True):
        super().__init__()
        self.inc = DoubleConv(n_channels, 64)
        self.down1 = Down(64, 128)
        self.down2 = Down(128, 256)
        self.down3 = Down(256, 512)
        factor = 2 if bilinear else 1
        self.down4 = Down(512, 1024 // factor)
        self.up1 = Up(1024, 512 // factor, bilinear)
        self.up2 = Up(512, 256 // factor, bilinear)
        self.up3 = Up(256, 128 // factor, bilinear)
        self.up4 = Up(128, 64, bilinear)
        self.outc = OutConv(64, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        return self.outc(x)


class DiceLoss(nn.Module):
    def __init__(self, smooth: float = 1.0):
        super().__init__()
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        probs = torch.sigmoid(logits)
        probs = probs.view(-1)
        targets = targets.view(-1)
        intersection = (probs * targets).sum()
        dice = (2 * intersection + self.smooth) / (probs.sum() + targets.sum() + self.smooth)
        return 1 - dice


class CombinedLoss(nn.Module):
    def __init__(self, bce_weight: float = 0.5, dice_weight: float = 0.5):
        super().__init__()
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight
        self.bce = nn.BCEWithLogitsLoss()
        self.dice = DiceLoss()

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce_loss = self.bce(logits, targets)
        dice_loss = self.dice(logits, targets)
        return self.bce_weight * bce_loss + self.dice_weight * dice_loss


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
) -> float:
    model.train()
    running_loss = 0.0
    for images, masks in loader:
        images = images.to(device)
        masks = masks.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(images)
        loss = criterion(logits, masks)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
    return running_loss / max(1, len(loader))


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device) -> float:
    model.eval()
    running_loss = 0.0
    for images, masks in loader:
        images = images.to(device)
        masks = masks.to(device)
        logits = model(images)
        loss = criterion(logits, masks)
        running_loss += loss.item()
    return running_loss / max(1, len(loader))


def save_checkpoint(model: nn.Module, path: Path, config: TrainConfig, epoch: int, val_loss: float) -> None:
    torch.save(
        {
            "model": model.state_dict(),
            "config": asdict(config),
            "epoch": epoch,
            "val_loss": val_loss,
        },
        path,
    )


def preprocess_image(image_path: Path, image_size: Tuple[int, int]) -> torch.Tensor:
    image = Image.open(image_path).convert("RGB").resize(image_size, Image.BILINEAR)
    array = np.asarray(image, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(array.transpose(2, 0, 1))
    return tensor.unsqueeze(0)


@torch.no_grad()
def predict_mask(model: nn.Module, tensor: torch.Tensor, device: torch.device, threshold: float) -> np.ndarray:
    logits = model(tensor.to(device))
    probs = torch.sigmoid(logits)
    mask = (probs > threshold).float().cpu().numpy()
    return mask


def train_cli(args: argparse.Namespace) -> None:
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = TrainConfig(
        image_size=(args.image_size[0], args.image_size[1]),
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        weight_decay=args.weight_decay,
        val_split=args.val_split,
        num_workers=args.workers,
        seed=args.seed,
        bce_weight=args.bce_weight,
        dice_weight=args.dice_weight,
    )

    seed_everything(config.seed)

    dataset_dir = Path(args.dataset_dir).expanduser()
    images, masks = load_lane_pairs(dataset_dir)
    train_loader, val_loader = create_dataloaders(images, masks, config)
    device = get_device()

    model = UNet(n_channels=3, n_classes=1, bilinear=not args.no_bilinear).to(device)
    criterion = CombinedLoss(config.bce_weight, config.dice_weight)
    optimizer = optim.Adam(model.parameters(), lr=config.lr, weight_decay=config.weight_decay)

    best_val = float("inf")
    for epoch in range(1, config.epochs + 1):
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss = evaluate(model, val_loader, criterion, device)
        print(f"[Epoch {epoch}/{config.epochs}] train={train_loss:.4f} | val={val_loss:.4f}")
        if val_loss < best_val:
            best_val = val_loss
            save_checkpoint(model, output_path, config, epoch, val_loss)
            print(f"→ 새로운 최적 가중치 저장: {output_path}")

    print(f"학습 완료! 최적 검증 손실: {best_val:.4f}")


def predict_cli(args: argparse.Namespace) -> None:
    checkpoint = Path(args.checkpoint).expanduser()
    device = get_device()

    model = UNet(n_channels=3, n_classes=1, bilinear=not args.no_bilinear).to(device)
    state = torch.load(checkpoint, map_location=device)
    weights = state["model"] if isinstance(state, dict) and "model" in state else state
    model.load_state_dict(weights)
    model.eval()

    tensor = preprocess_image(Path(args.image).expanduser(), (args.image_size[0], args.image_size[1]))
    mask = predict_mask(model, tensor, device, args.threshold)

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mask_img = Image.fromarray((mask.squeeze(0) * 255).astype(np.uint8))
    mask_img.save(output_path)
    print(f"마스크 저장 완료: {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UNet 차선 분할 학습/추론 스크립트")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="차선 분할 모델 학습")
    train_parser.add_argument("--dataset-dir", type=str, default=str(DEFAULT_DATASET_DIR), help="이미지/마스크 루트 경로")
    train_parser.add_argument("--output", type=str, default=str(DEFAULT_MODEL_PATH), help="학습된 가중치 저장 경로")
    train_parser.add_argument("--image-size", type=int, nargs=2, default=(256, 256), metavar=("WIDTH", "HEIGHT"))
    train_parser.add_argument("--epochs", type=int, default=50)
    train_parser.add_argument("--batch-size", type=int, default=8)
    train_parser.add_argument("--lr", type=float, default=1e-4)
    train_parser.add_argument("--weight-decay", type=float, default=1e-5)
    train_parser.add_argument("--val-split", type=float, default=0.2)
    train_parser.add_argument("--workers", type=int, default=4)
    train_parser.add_argument("--seed", type=int, default=42)
    train_parser.add_argument("--bce-weight", type=float, default=0.5)
    train_parser.add_argument("--dice-weight", type=float, default=0.5)
    train_parser.add_argument("--no-bilinear", action="store_true", help="업샘플 시 bilinear 대신 ConvTranspose 사용")
    train_parser.set_defaults(func=train_cli)

    predict_parser = subparsers.add_parser("predict", help="단일 이미지 차선 마스크 생성")
    predict_parser.add_argument("--checkpoint", type=str, default=str(DEFAULT_MODEL_PATH), help="학습된 가중치 경로(.pt)")
    predict_parser.add_argument("--image", type=str, required=True, help="입력 이미지 경로")
    predict_parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_MASK), help="출력 마스크 저장 경로")
    predict_parser.add_argument("--image-size", type=int, nargs=2, default=(256, 256), metavar=("WIDTH", "HEIGHT"))
    predict_parser.add_argument("--threshold", type=float, default=0.5, help="시그모이드 출력 임계값")
    predict_parser.add_argument("--no-bilinear", action="store_true", help="학습 시와 동일하게 ConvTranspose 사용 여부")
    predict_parser.set_defaults(func=predict_cli)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
