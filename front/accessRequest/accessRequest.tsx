import { Camera } from "expo-camera";
import { Audio } from "expo-av";

export default async function requestPermissions() {
  const { status: camStatus } = await Camera.requestCameraPermissionsAsync();
  const { status: micStatus } = await Audio.requestPermissionsAsync();

  if (camStatus !== "granted" || micStatus !== "granted") {
    alert("카메라/마이크 권한이 필요합니다.");
    return false;
  }
  return true;
}
