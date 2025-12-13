import React from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
  Pressable,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons, MaterialIcons } from "@expo/vector-icons";

/** 임시 더미 데이터 (백엔드 연결 전 테스트용) */
const mock = {
  date: "2024-01-15",
  startTime: "14:30 출발",
  drivingMinutes: 45,
  video: {
    duration: "45:23",
    size: "1.2GB",
    quality: "HD",
    thumbnail:
      "https://images.unsplash.com/photo-1502877338535-766e1452684a?q=80&w=1600&auto=format&fit=crop",
  },
  events: [
    {
      id: 1,
      type: "distance",
      title: "앞차와의 거리가 너무 가깝습니다",
      time: "45:00",
      clipAt: "00:05:23",
      color: "#F59E0B",
      icon: <Ionicons name="warning-outline" size={18} color="#fff" />,
    },
    {
      id: 2,
      type: "hard-brake",
      title: "급정거가 감지되었습니다",
      time: "45:00",
      clipAt: "00:12:15",
      color: "#F97373",
      icon: <MaterialIcons name="safety-check" size={18} color="#fff" />,
    },
    {
      id: 3,
      type: "signal",
      title: "신호등 감지",
      time: "45:00",
      clipAt: "00:28:45",
      color: "#60A5FA",
      icon: <Ionicons name="information" size={18} color="#fff" />,
    },
  ],
};

type EventItemProps = {
  title: string;
  time: string;
  clipAt: string;
  color: string;
  icon: React.ReactNode;
  onPress?: () => void;
};

const EventItem = ({
  title,
  time,
  clipAt,
  color,
  icon,
  onPress,
}: EventItemProps) => (
  <View style={styles.eventCard}>
    <View style={styles.eventRow}>
      <View style={[styles.eventBadge, { backgroundColor: color }]}>{icon}</View>
      <Text style={styles.eventTitle} numberOfLines={2}>
        {title}
      </Text>
    </View>

    <View style={styles.eventMetaRow}>
      <Ionicons name="time-outline" size={14} color="#6B7280" />
      <Text style={styles.dot}>총 주행 시간 :</Text>
      <Text style={styles.eventMetaText}>{time}</Text>
    </View>

    <Pressable onPress={onPress} style={styles.playChip}>
      <Ionicons name="play-circle-outline" size={16} color="#111827" />
      <Text style={styles.playChipText}>영상 재생 ({clipAt})</Text>
    </Pressable>
  </View>
);

type Props = {
  id: string; // 부모에서 넘겨주는 주행 id
  onClose?: () => void; // 닫기(선택)
};

/** 전체화면 모달 형태의 상세 */
export const RecordDetails = ({ id, onClose }: Props) => {
  const data = mock;

  return (
    <View style={styles.overlay}>
      {/* SafeAreaView는 상단/좌/우만, 배경은 안쪽 sheet에서 처리 */}
      <SafeAreaView style={{ flex: 1 }} edges={["top", "left", "right"]}>
        <View style={styles.sheet}>
          {/* 상단 바 (제목 + 닫기) */}
          <View style={styles.topBar}>
            <Text style={styles.topTitle}>주행 상세</Text>
            <TouchableOpacity
              onPress={onClose}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <Ionicons name="close" size={22} color="#111827" />
            </TouchableOpacity>
          </View>

          <ScrollView
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            {/* 헤더 카드 (id 출력 포함) */}
            <View style={styles.headerCard}>
              <View>
                <Text style={styles.dateText}>{data.date}</Text>
                <Text style={styles.subText}>{data.startTime}</Text>
              </View>
              <View style={styles.durationBox}>
                <Text style={styles.durationBig}>{data.drivingMinutes}분</Text>
                <Text style={styles.durationSub}>주행 시간</Text>
              </View>
            </View>

            {/* 주행 기록 영상 */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>운전 기록 영상</Text>
              <View style={styles.videoCard}>
                <Image
                  source={{ uri: data.video.thumbnail }}
                  style={styles.videoImage}
                />
                <View style={styles.videoOverlay}>
                  <TouchableOpacity
                    onPress={() => {
                      // TODO: 비디오 플레이어로 이동/재생
                    }}
                    style={styles.playButton}
                  >
                    <Ionicons name="play" size={28} color="#111827" />
                  </TouchableOpacity>

                  <View style={styles.videoMetaLeft}>
                    <Text style={styles.videoMetaBadge}>
                      {data.video.duration}
                    </Text>
                  </View>

                  <View style={styles.videoMetaRight}>
                    <Text style={styles.videoQuality}>{data.video.quality}</Text>
                  </View>
                </View>
              </View>

              <View style={styles.videoFootRow}>
                <Text style={styles.footMuted}>용량: {data.video.size}</Text>
              </View>
            </View>

            {/* 이벤트 리스트 */}
            <View style={styles.section}>
              <View style={styles.sectionHeaderRow}>
                <Text style={styles.sectionTitle}>주행 이벤트</Text>
                <Text style={styles.sectionCount}>{data.events.length}개</Text>
              </View>

              {data.events.map((ev) => (
                <EventItem
                  key={ev.id}
                  title={ev.title}
                  time={ev.time}
                  clipAt={ev.clipAt}
                  color={ev.color}
                  icon={ev.icon}
                  onPress={() => {
                    // TODO: 특정 시점부터 영상 재생
                  }}
                />
              ))}
            </View>

            {/* 하단 여백 (스크롤 여유) */}
            <View style={{ height: 16 }} />
          </ScrollView>

          {/* 하단 고정 버튼들 */}
          <View style={styles.bottomBar}>
            <TouchableOpacity
              style={[styles.primaryBtn, { backgroundColor: "#9CA3AF" }]}
              onPress={onClose}
            >
              <Ionicons name="close" size={18} color="#fff" />
              <Text style={styles.primaryBtnText}>닫기</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.primaryBtn,
                { backgroundColor: "#2563EB", marginTop: 10 },
              ]}
              onPress={() => {
                // TODO: 전체 주행 영상 보기
              }}
            >
              <Ionicons name="play" size={18} color="#fff" />
              <Text style={styles.primaryBtnText}>전체 주행 영상 보기</Text>
            </TouchableOpacity>
          </View>
        </View>
      </SafeAreaView>
    </View>
  );
};

/** 스타일 */
const styles = StyleSheet.create({
  /** 전체 화면 덮개 (뒤 배경 어둡게) */
  overlay: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    backgroundColor: "rgba(0,0,0,0.5)",
  },

  /** 시트 = 실제 모달 컨테이너 */
  sheet: {
    flex: 1,
    backgroundColor: "#F2F4F7", // 안쪽 배경
  },

  topBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: "#fff",
  },
  topTitle: {
    fontSize: 16,
    fontWeight: "800",
    color: "#111827",
    flex: 1,
  },

  // ★ 하단 버튼이 가리지 않도록 paddingBottom 추가
  scrollContent: {
    padding: 16,
    paddingBottom: 80,
  },

  /* 헤더 카드 */
  headerCard: {
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 16,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  dateText: { fontSize: 18, fontWeight: "700", color: "#111827" },
  subText: { marginTop: 4, fontSize: 14, color: "#6B7280" },
  durationBox: { alignItems: "flex-end" },
  durationBig: { fontSize: 20, fontWeight: "800", color: "#2563EB" },
  durationSub: { fontSize: 12, color: "#6B7280", marginTop: 4 },

  /* 공통 섹션 */
  section: { marginTop: 18 },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "800",
    color: "#111827",
    marginBottom: 12,
  },
  sectionHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },
  sectionCount: { marginLeft: "auto", color: "#6B7280", fontWeight: "700" },

  /* 비디오 카드 */
  videoCard: {
    backgroundColor: "#fff",
    borderRadius: 14,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  videoImage: { width: "100%", height: 210 },
  videoOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: "center",
    alignItems: "center",
  },
  playButton: {
    backgroundColor: "#fff",
    borderRadius: 999,
    width: 56,
    height: 56,
    alignItems: "center",
    justifyContent: "center",
  },
  videoMetaLeft: { position: "absolute", left: 12, bottom: 12 },
  videoMetaRight: {
    position: "absolute",
    right: 12,
    bottom: 12,
    backgroundColor: "#111827",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  videoMetaBadge: {
    backgroundColor: "rgba(17,24,39,0.85)",
    color: "#fff",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    fontSize: 12,
    overflow: "hidden",
  },
  videoQuality: { color: "#fff", fontWeight: "800", fontSize: 12 },
  videoFootRow: { paddingTop: 8, paddingHorizontal: 4 },
  footMuted: { color: "#6B7280", fontSize: 12 },

  /* 이벤트 카드 */
  eventCard: {
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
  eventRow: { flexDirection: "row", alignItems: "center" },
  eventBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 10,
  },
  eventTitle: { flex: 1, fontSize: 16, fontWeight: "700", color: "#111827" },
  eventMetaRow: { marginTop: 8, flexDirection: "row", alignItems: "center" },
  eventMetaText: { fontSize: 13, color: "#6B7280", marginLeft: 4 },
  dot: { marginHorizontal: 6, color: "#9CA3AF" },
  playChip: {
    alignSelf: "flex-start",
    marginTop: 12,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#E5E7EB",
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 10,
  },
  playChipText: { fontWeight: "700", color: "#111827", fontSize: 13 },

  /* 하단 버튼 영역 */
  bottomBar: {
    padding: 16,
    backgroundColor: "transparent",
  },
  primaryBtn: {
    height: 52,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 8,
  },
  primaryBtnText: { color: "#fff", fontSize: 16, fontWeight: "800" },
});
