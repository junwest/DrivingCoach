import React from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { PageHeaderD } from "../../Driving/PageHeaderD";
import { useNavigation } from "@react-navigation/native";
export default function DrivingScreen() {
  const navigation = useNavigation();
    return (
    <SafeAreaView style={styles.container}>
      <PageHeaderD />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* 주행 시작 카드 */}
        <View style={styles.card}>
          <View style={styles.iconCircle}>
            <Ionicons name="car-sport-outline" size={40} color="#3478F6" />
          </View>
          <Text style={styles.cardTitle}>주행을 시작하시겠습니까?</Text>
          <Text style={styles.cardSubtitle}>AI가 실시간으로 안전 운전을 도와드립니다</Text>
          <TouchableOpacity style={styles.startButton}
          onPress={() => navigation.navigate("DrivingReady" as never)}
       >
            <Text style={styles.startButtonText}>주행 시작</Text>
          </TouchableOpacity>
        </View>

        {/* 체크리스트 */}
        <View style={styles.card}>
          <Text style={styles.checklistTitle}>주행 전 체크리스트</Text>
          <View style={styles.checkItem}>
            <Ionicons name="checkmark-circle" size={20} color="green" />
            <Text style={styles.checkText}>안전벨트 착용</Text>
          </View>
          <View style={styles.checkItem}>
            <Ionicons name="checkmark-circle" size={20} color="green" />
            <Text style={styles.checkText}>사이드미러 조정</Text>
          </View>
          <View style={styles.checkItem}>
            <Ionicons name="checkmark-circle" size={20} color="green" />
            <Text style={styles.checkText}>휴대폰 거치대 설치</Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F5F5F5",
  },
  scrollContent: {
    padding: 20,
  },
  card: {
    backgroundColor: "white",
    borderRadius: 15,
    padding: 20,
    marginBottom: 20,
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 3,
  },
  iconCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "#EAF1FF",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 15,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "bold",
    marginBottom: 6,
    textAlign: "center",
  },
  cardSubtitle: {
    fontSize: 14,
    color: "#666",
    marginBottom: 15,
    textAlign: "center",
  },
  startButton: {
    backgroundColor: "#3478F6",
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 30,
  },
  startButtonText: {
    color: "white",
    fontWeight: "bold",
    fontSize: 16,
  },
  checklistTitle: {
    fontSize: 16,
    fontWeight: "bold",
    marginBottom: 15,
    alignSelf: "flex-start",
  },
  checkItem: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
    alignSelf: "flex-start",
  },
  checkText: {
    fontSize: 14,
    marginLeft: 8,
  },
});
