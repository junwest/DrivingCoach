from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import librosa
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
MODEL_DIR = PROJECT_ROOT / "model_save"
MODEL_PATH = MODEL_DIR / "best.pt"

CLASS_NAMES = ["blinker", "horn", "wiper", "normal"]


@dataclass
class Config:
    sr: int = 16000
    duration: float = 2.0
    n_mels: int = 64
    n_fft: int = 1024
    hop_length: int = 256
    batch_size: int = 32
    epochs: int = 30
    lr: float = 1e-3
    val_split: float = 0.2
    seed: int = 42


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(False)


class AudioDataset(Dataset):
    def __init__(self, file_paths: Sequence[Path], labels: Sequence[int], config: Config):
        self.file_paths = list(file_paths)
        self.labels = list(labels)
        self.config = config
        self.target_len = int(config.sr * config.duration)

    def __len__(self) -> int:
        return len(self.file_paths)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        file_path = self.file_paths[idx]
        label = self.labels[idx]

        y, _ = librosa.load(file_path, sr=self.config.sr)
        if len(y) < self.target_len:
            y = np.pad(y, (0, self.target_len - len(y)))
        else:
            y = y[: self.target_len]

        mel_spec = librosa.feature.melspectrogram(
            y=y,
            sr=self.config.sr,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length,
            n_mels=self.config.n_mels,
        )
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        mel_spec_db = (mel_spec_db - mel_spec_db.mean()) / (mel_spec_db.std() + 1e-6)
        tensor = torch.tensor(mel_spec_db, dtype=torch.float32).unsqueeze(0)
        return tensor, torch.tensor(label, dtype=torch.long)


class AudioCNN(nn.Module):
    def __init__(self, num_classes: int = len(CLASS_NAMES)):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        return self.classifier(x)


def load_file_paths(data_dir: Path) -> Tuple[List[Path], List[int]]:
    all_files: List[Path] = []
    all_labels: List[int] = []
    for idx, class_name in enumerate(CLASS_NAMES):
        class_dir = data_dir / class_name
        if not class_dir.exists():
            print(f"경고: {class_dir} 폴더가 없습니다. 건너뜁니다.")
            continue
        for wav_path in sorted(class_dir.glob("*.wav")):
            all_files.append(wav_path)
            all_labels.append(idx)
    if not all_files:
        raise FileNotFoundError(f"{data_dir} 에서 .wav 파일을 찾을 수 없습니다.")
    return all_files, all_labels


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def train_one_epoch(model: nn.Module, loader: DataLoader, criterion, optimizer, device: torch.device) -> float:
    model.train()
    running_loss = 0.0
    for inputs, labels in loader:
        inputs, labels = inputs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
    return running_loss / len(loader)


def evaluate(model: nn.Module, loader: DataLoader, criterion, device: torch.device) -> Tuple[float, float]:
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, labels in loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            running_loss += loss.item()
            preds = outputs.argmax(dim=1)
            total += labels.size(0)
            correct += (preds == labels).sum().item()
    return running_loss / len(loader), (correct / total) * 100


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4-class audio classifier training")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Config(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        val_split=args.val_split,
        seed=args.seed,
    )

    seed_everything(config.seed)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    device = get_device()
    print(f"Using device: {device}")
    print("데이터 로딩 중...")
    all_files, all_labels = load_file_paths(DATASET_DIR)

    train_files, val_files, train_labels, val_labels = train_test_split(
        all_files,
        all_labels,
        test_size=config.val_split,
        random_state=config.seed,
        stratify=all_labels,
    )

    train_dataset = AudioDataset(train_files, train_labels, config)
    val_dataset = AudioDataset(val_files, val_labels, config)

    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=config.batch_size, shuffle=False, num_workers=0)

    print(f"학습 데이터: {len(train_dataset)}개, 검증 데이터: {len(val_dataset)}개")

    model = AudioCNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=config.lr)

    best_acc = 0.0
    for epoch in range(1, config.epochs + 1):
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)
        print(
            f"Epoch [{epoch}/{config.epochs}] "
            f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}%"
        )

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), MODEL_PATH)
            print(f"  -> 새로운 최고 성능! 모델 저장: {MODEL_PATH} (Val Acc {best_acc:.2f}%)")

    print("학습 완료!")
    print(f"최고 검증 정확도: {best_acc:.2f}%")
    print(f"베스트 모델 경로: {MODEL_PATH}")


if __name__ == "__main__":
    main()