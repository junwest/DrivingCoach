import React, { useRef, useState, useEffect } from "react";
import { View, Button, StyleSheet, Text, Alert, Modal, ActivityIndicator } from "react-native";
import { Camera, CameraView } from "expo-camera";
import { Audio } from "expo-av";
import * as Speech from "expo-speech";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useNavigation, CommonActions } from "@react-navigation/native";
import { useWebSocket } from "./context/WebSocketContext";
import { fileUriToArrayBuffer, zipSingleFileIfAvailable } from "../utils/wsHelpers";

// ★ 화면 회전 제어 라이브러리
import * as ScreenOrientation from 'expo-screen-orientation';

const HOST = "15.165.244.204:8080"; // 백엔드 주소
const API_URL = `http://${HOST}`;

export default function Driving() {
  const navigation = useNavigation<any>();
  const cameraRef = useRef<CameraView | null>(null);
  const { connect, close, sendJson, sendBinary, onceOpen, ref: wsRef } = useWebSocket();

  const [jwt, setJwt] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  
  // 백엔드에서 받은 recordId 저장
  const currentRecordIdRef = useRef<number | null>(null);

  const drivingLoopRef = useRef(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const [camPerm, setCamPerm] = useState(false);
  const [audPerm, setAudPerm] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);

  const [stopping, setStopping] = useState(false);
  const [statusMessage, setStatusMessage] = useState(""); 

  // ----------------------------------------------------------------
  // ★ [수정] 화면 가로 모드(반대 방향) 고정 & 탭바 숨기기
  // ----------------------------------------------------------------
  useEffect(() => {
    const lockLandscapeAndHideTab = async () => {
      try {
        // 1. 탭바 숨기기 (부모 네비게이터인 Tab.Navigator에 옵션 설정)
        navigation.getParent()?.setOptions({
          tabBarStyle: { display: "none" }
        });

        // 2. 가로 모드 고정 (LANDSCAPE_LEFT: 윗부분이 왼쪽)
        await ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.LANDSCAPE_LEFT);
      } catch (e) {
        console.warn("화면 설정 실패:", e);
      }
    };

    lockLandscapeAndHideTab();

    // 화면을 벗어날 때(Unmount) 원상복구
    return () => {
      const restoreScreen = async () => {
        try {
          // 1. 세로 모드로 복귀
          await ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.PORTRAIT_UP);
          
          // 2. 탭바 다시 보이기
          navigation.getParent()?.setOptions({
            tabBarStyle: undefined // 기본값으로 복원 (보임)
          });
        } catch (e) {
          console.warn("화면 복구 실패:", e);
        }
      };
      restoreScreen();
    };
  }, [navigation]);
  // ----------------------------------------------------------------


  // 1. 토큰 로드
  useEffect(() => {
    (async () => {
      const token = await AsyncStorage.getItem("accessToken");
      if (!token) {
        Alert.alert("로그인 필요", "다시 로그인해주세요.");
        return;
      }
      setJwt(token);
    })();
  }, []);

  // 2. 권한 요청
  useEffect(() => {
    (async () => {
      const { status: cs } = await Camera.requestCameraPermissionsAsync();
      setCamPerm(cs === "granted");
      const { status: ms } = await Camera.requestMicrophonePermissionsAsync();
      setAudPerm(ms === "granted");
      
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
      });
    })();
  }, []);

  // 3. 타이머
  useEffect(() => {
    if (recording && !timerRef.current)
      timerRef.current = setInterval(() => setElapsedTime((t) => t + 1), 1000);
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [recording]);

  // 4. WebSocket 메시지 리스너 (RecordID 획득 + TTS 음성 피드백)
  useEffect(() => {
    const ws = wsRef.current;
    if (!ws) return;

    const handleMessage = (e: WebSocketMessageEvent) => {
      try {
        const msg = JSON.parse(e.data);

        // (1) 주행 시작 메시지
        if (msg.type === 'STARTED' && msg.recordId) {
          console.log("[WS] ✅ 주행 시작됨! RecordID:", msg.recordId);
          currentRecordIdRef.current = msg.recordId;
        }

        // (2) AI 음성 피드백 처리 (TTS)
        if (msg.type === 'FEEDBACK_VOICE' && msg.message) {
          console.log("🔊 [TTS] 음성 안내:", msg.message);
          
          Speech.stop(); // 기존 음성 중단

          Speech.speak(msg.message, {
            language: "ko-KR",
            pitch: 1.0,
            rate: 1.0,
          });
        }

      } catch (err) {
        // ignore
      }
    };

    ws.addEventListener('message', handleMessage);
    return () => ws.removeEventListener('message', handleMessage);
  }, [wsRef.current, recording]);


  const formatTime = (n: number) =>
    `${String(Math.floor(n / 60)).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}`;

  // 영상 조각 녹화 (2초)
  const recordOneSegment = () =>
    new Promise<string>((resolve, reject) => {
      if (!cameraRef.current) return reject(new Error("camera not ready"));
      
      cameraRef.current
        .recordAsync({ maxDuration: 2 })
        .then((video) => {
          if (video?.uri) {
            resolve(video.uri);
          } else {
            reject(new Error("No video URI returned"));
          }
        })
        .catch((err) => {
          reject(err);
        });
    });

  // 5. 주행 종료 API 호출 및 네비게이션 리셋
  const finishDrivingSequence = async () => {
    console.log("[Finish] 주행 종료 요청");
    setStatusMessage("주행 기록 저장 중...");
    
    try {
      if (currentRecordIdRef.current) {
        // 백엔드에 종료 요청
        const response = await fetch(`${API_URL}/api/driving/end`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${jwt}`
            },
            body: JSON.stringify({
                recordId: currentRecordIdRef.current,
                endTime: new Date().toISOString(),
                finalScore: 100, // (예시) 점수
                finalVideoKeyOrUrl: null // 백엔드가 직접 병합하도록 null 전송
            })
        });
        
        if (response.ok) {
            console.log("[API] 주행 종료 성공");
        } else {
            console.error("[API] 주행 종료 실패", await response.text());
        }
      }

    } catch (e) {
      console.error("[Finish] 종료 에러:", e);
    } finally {
        setStopping(false);

        // 네비게이션 리셋 로직
        navigation.getParent()?.navigate("기록실");
        navigation.dispatch(
          CommonActions.reset({
            index: 0,
            routes: [{ name: 'DrivingScreen' }], 
          })
        );
    }
  };


  // --- 녹화 시작 ---
  const startRecording = async () => {
    if (recording) return;
    if (!camPerm || !audPerm) return Alert.alert("권한 필요", "권한 허용 필요");
    if (!cameraReady || !cameraRef.current) return Alert.alert("카메라 준비 중", "잠시만요");
    if (!jwt) return Alert.alert("오류", "토큰 없음");

    currentRecordIdRef.current = null;
    setStopping(false);

    try {
      Speech.speak("안전 운전을 시작합니다.", { language: "ko-KR" });

      // 웹소켓 연결
      const url = `ws://${HOST}/ws/driving?token=${encodeURIComponent(`Bearer ${jwt}`)}`;
      await connect(url);
      await onceOpen();
      sendJson({ type: "START" }); 

      setRecording(true);
      setElapsedTime(0);
      drivingLoopRef.current = true;

      // 녹화 루프
      let nextPromise: Promise<string> | null = null;
      
      while (drivingLoopRef.current) {
        // (A) 녹화
        const uri = nextPromise ? await nextPromise : await recordOneSegment();
        
        if (drivingLoopRef.current) {
             nextPromise = recordOneSegment();
        } else {
             nextPromise = null;
        }

        // (B) 실시간 전송
        const path = await zipSingleFileIfAvailable(uri);
        const buf = await fileUriToArrayBuffer(path);
        sendBinary(buf);
      }

    } catch (e) {
      console.warn("startRecording error:", e);
      Alert.alert("오류", "녹화 시작 실패");
      setRecording(false);
    }
  };

  // --- 녹화 종료 ---
  const stopRecording = async () => {
    console.log("[Driving] 종료 버튼 클릭");
    if (!recording) return;
    
    Speech.stop();
    setStopping(true);
    
    drivingLoopRef.current = false; 
    
    try { cameraRef.current?.stopRecording(); } catch {}
    setRecording(false);

    // 웹소켓 END 전송
    if (wsRef.current?.readyState === WebSocket.OPEN) {
        sendJson({ type: "END" });
    }
    close(); 

    // 종료 API 호출
    await finishDrivingSequence();
  };

  return (
    <View style={{ flex: 1 }}>
      <CameraView
        ref={cameraRef}
        style={{ flex: 1 }}
        facing="back"
        mode="video"
        videoQuality="480p"
        onCameraReady={() => setCameraReady(true)}
      />

      <View style={styles.timeContainer}>
        <Text style={styles.timeText}>{formatTime(elapsedTime)}</Text>
      </View>

      <View style={styles.buttonContainer}>
        <Button
          title={recording ? "주행 종료" : "주행 시작"}
          onPress={recording ? stopRecording : startRecording}
          disabled={stopping}
          color={recording ? "#DC2626" : "#3478F6"}
        />
      </View>

      {/* 종료 중 로딩 모달 */}
      <Modal visible={stopping} transparent animationType="fade">
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <ActivityIndicator size="large" color="#3478F6" />
            <Text style={styles.modalText}>주행 종료 중...</Text>
            <Text style={styles.modalSub}>{statusMessage}</Text>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  buttonContainer: { position: "absolute", bottom: 40, alignSelf: "center", width: "80%" },
  timeContainer: {
    position: "absolute",
    top: 50,
    alignSelf: "center",
    backgroundColor: "rgba(0,0,0,0.5)",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  timeText: { fontSize: 24, fontWeight: "bold", color: "white" },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.6)",
    justifyContent: "center",
    alignItems: "center",
  },
  modalCard: {
    width: 280,
    borderRadius: 16,
    backgroundColor: "white",
    paddingVertical: 28,
    paddingHorizontal: 24,
    alignItems: "center",
    elevation: 5,
  },
  modalText: { marginTop: 16, fontSize: 18, fontWeight: "bold", color: "#111827" },
  modalSub: { marginTop: 8, fontSize: 14, color: "#6B7280", textAlign: "center" },
});