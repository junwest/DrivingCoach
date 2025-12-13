// utils/wsHelpers.ts
import * as FileSystem from "expo-file-system/legacy";

// (ZIP 미사용 설정) 필요 시 실제 네이티브 모듈 연결해서 복구 가능
let RNZipArchive: { zip: (src: string, dest: string) => Promise<string> } | null = null;
try {
  RNZipArchive = require("react-native-zip-archive");
} catch {
  RNZipArchive = null;
}

export function b64ToArrayBuffer(b64: string): ArrayBuffer {
  const binary = global.atob
    ? global.atob(b64 ?? "")
    : Buffer.from(b64 ?? "", "base64").toString("binary");
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

export async function fileUriToArrayBuffer(uri: string): Promise<ArrayBuffer> {
  try {
    const normalized = decodeURI(uri);
    const response = await fetch(normalized);
    const blob = await response.blob();
    return new Promise<ArrayBuffer>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (reader.result instanceof ArrayBuffer) resolve(reader.result);
        else reject(new Error("Failed to read blob as ArrayBuffer"));
      };
      reader.onerror = () => reject(reader.error);
      reader.readAsArrayBuffer(blob);
    });
  } catch (e) {
    console.warn("fetch 방식 실패, 재시도:", e);
    try {
      const normalized = decodeURI(uri);
      const b64 = await FileSystem.readAsStringAsync(normalized, {
        encoding: "base64" as any,
      });
      return b64ToArrayBuffer(b64);
    } catch (fallbackError) {
      console.error("fileUriToArrayBuffer 최종 실패:", fallbackError);
      throw fallbackError;
    }
  }
}

// ★ ZIP 생략: 항상 원본 파일 경로 반환
export async function zipSingleFileIfAvailable(fileUri: string): Promise<string> {
  return fileUri;
  // 필요 시:
  // if (!RNZipArchive) return fileUri;
  // const target = fileUri.replace(/\.mp4$/i, "") + ".zip";
  // try {
  //   await RNZipArchive.zip(fileUri, target);
  //   return target;
  // } catch (e) {
  //   console.warn("zip 실패, 원본 사용:", e);
  //   return fileUri;
  // }
}
