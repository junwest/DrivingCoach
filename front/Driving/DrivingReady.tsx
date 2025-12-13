// DrivingReady.tsx
import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, ActivityIndicator } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { Camera } from "expo-camera";
import { Audio } from "expo-av";

export default function DrivingReady() {
  const navigation = useNavigation();
  const [status, setStatus] = useState("주행 준비중...");

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const camRes = await Camera.requestCameraPermissionsAsync();
        const micRes = await Audio.requestPermissionsAsync();

        if (!mounted) return;
        if (camRes.status !== "granted" || micRes.status !== "granted") {
          setStatus("권한 거부됨");
          setTimeout(() => navigation.navigate("DrivingScreen" as never), 800);
          return;
        }
        setStatus("준비 완료! 주행 화면으로 이동합니다...");
        setTimeout(() => navigation.navigate("Driving" as never), 300);
      } catch (e) {
        if (!mounted) return;
        setStatus("준비 중 오류");
        console.warn(e);
      }
    })();
    return () => { mounted = false; };
  }, [navigation]);

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#3478F6" />
      <Text style={styles.text}>{status}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", alignItems: "center" },
  text: { marginTop: 20, fontSize: 16, color: "#333" },
});
