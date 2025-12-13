import React, { useMemo, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Switch,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import Slider from "@react-native-community/slider";

// 헤더
import { PageHeaderD } from "../../SettingScreenComponents/pageHeaderD";

type VoiceGender = "male" | "female";

export default function SettingScreen() {
  const [gender, setGender] = useState<VoiceGender>("female");
  const [volume, setVolume] = useState<number>(0.7); // 0 ~ 1
  const [vibrateAlert, setVibrateAlert] = useState<boolean>(true);

  const volumePercent = useMemo(() => Math.round(volume * 100), [volume]);

  const onPressItem = (key: "app" | "support" | "terms" | "privacy") => {
    // TODO: 네비게이션 or 링크 연결
    console.log("open:", key);
  };

  return (
    <SafeAreaView style={styles.container}>
      <PageHeaderD />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* 음성 설정 */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>음성 설정</Text>

          <Text style={styles.caption}>음성 피드백</Text>
          {/* ▶ 수정된 세그먼트: 남/여 모두 동일한 형태로 보임 */}
          <View style={styles.segment}>
            <TouchableOpacity
              style={[styles.segmentBtn, gender === "male" && styles.segmentBtnActive]}
              onPress={() => setGender("male")}
              activeOpacity={0.9}
            >
              <Text style={[styles.segmentText, gender === "male" && styles.segmentTextActive]}>
                남성 음성
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.segmentBtn, gender === "female" && styles.segmentBtnActive]}
              onPress={() => setGender("female")}
              activeOpacity={0.9}
            >
              <Text style={[styles.segmentText, gender === "female" && styles.segmentTextActive]}>
                여성 음성
              </Text>
            </TouchableOpacity>
          </View>

          <Text style={[styles.caption, { marginTop: 18 }]}>음량 ({volumePercent}%)</Text>
          <Slider
            style={{ width: "100%", height: 36 }}
            minimumValue={0}
            maximumValue={1}
            step={0.01}
            value={volume}
            onValueChange={setVolume}
            minimumTrackTintColor="#2563EB"
            maximumTrackTintColor="#E5E7EB"
            thumbTintColor="#2563EB"
          />

          <View style={styles.rowBetween}>
            <View>
              <Text style={styles.cardTitleSmall}>진동 알림</Text>
              <Text style={styles.subtle}>경고 시 진동으로 알림</Text>
            </View>
            <Switch
              value={vibrateAlert}
              onValueChange={setVibrateAlert}
              trackColor={{ false: "#E5E7EB", true: "#93C5FD" }}
              thumbColor={vibrateAlert ? "#2563EB" : "#9CA3AF"}
            />
          </View>
        </View>

        {/* 기타 */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>기타</Text>

          <TouchableOpacity style={styles.itemRow} onPress={() => onPressItem("app")}>
            <Ionicons name="information-circle-outline" size={18} color="#6B7280" />
            <Text style={styles.itemText}>앱 정보</Text>
            <Ionicons name="chevron-forward" size={18} color="#9CA3AF" style={{ marginLeft: "auto" }} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.itemRow} onPress={() => onPressItem("support")}>
            <Ionicons name="headset-outline" size={18} color="#6B7280" />
            <Text style={styles.itemText}>고객 지원</Text>
            <Ionicons name="chevron-forward" size={18} color="#9CA3AF" style={{ marginLeft: "auto" }} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.itemRow} onPress={() => onPressItem("terms")}>
            <Ionicons name="document-text-outline" size={18} color="#6B7280" />
            <Text style={styles.itemText}>이용약관</Text>
            <Ionicons name="chevron-forward" size={18} color="#9CA3AF" style={{ marginLeft: "auto" }} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.itemRow} onPress={() => onPressItem("privacy")}>
            <Ionicons name="shield-checkmark-outline" size={18} color="#6B7280" />
            <Text style={styles.itemText}>개인정보처리방침</Text>
            <Ionicons name="chevron-forward" size={18} color="#9CA3AF" style={{ marginLeft: "auto" }} />
          </TouchableOpacity>
        </View>

        <View style={{ height: 24 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F5F5F5" },
  scrollContent: { padding: 16, paddingBottom: 32 },

  /* 공통 카드 */
  card: {
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 3 },
    elevation: 1,
  },
  cardTitle: { fontSize: 16, fontWeight: "800", color: "#111827", marginBottom: 12 },
  cardTitleSmall: { fontSize: 15, fontWeight: "700", color: "#111827" },
  subtle: { color: "#6B7280", marginTop: 4, fontSize: 12 },

  /* 세그먼트 */
  caption: { color: "#6B7280", fontSize: 12, marginBottom: 8 },
  segment: {
    flexDirection: "row",
    backgroundColor: "#EEF2FF",
    borderRadius: 12,
    padding: 4, // 내부 패딩으로 여백 처리 (버튼 사이 마진 X)
  },
  segmentBtn: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: "#fff",
  },
  segmentBtnActive: {
    backgroundColor: "#2563EB",
  },
  segmentText: { fontWeight: "700", color: "#111827" },
  segmentTextActive: { color: "#fff" },

  /* 행 */
  rowBetween: {
    marginTop: 14,
    paddingTop: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: "#E5E7EB",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },

  /* 리스트 아이템 */
  itemRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: "#F1F5F9",
  },
  itemText: { marginLeft: 8, color: "#111827", fontWeight: "600", fontSize: 14 },
});
