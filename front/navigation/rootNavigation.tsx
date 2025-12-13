import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { NavigationContainer } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";

// 각 화면 임시 컴포넌트
import HomeScreen from "../screens/tabNavScreens/HomeScreen";
import DrivingScreen from "../screens/tabNavScreens/DrivingScreen";
import DrivingStack from "./DrivingStack";
import RecordScreen from "../screens/tabNavScreens/RecordScreen";
import SettingScreen from "../screens/tabNavScreens/SettingScreen";
import MyPageScreen from "../screens/tabNavScreens/MyPageScreen";

const Tab = createBottomTabNavigator();

export default function RootNavigation() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarIcon: ({ color, size }) => {
            let iconName: keyof typeof Ionicons.glyphMap = "home";

            if (route.name === "홈") {
              iconName = "home";
            } else if (route.name === "주행") {
              iconName = "car";
            } else if (route.name === "기록실") {
              iconName = "time";
            }  else if (route.name === "마이페이지") {
              iconName = "person";
            }
            return <Ionicons name={iconName} size={size} color={color} />;
          },
          tabBarActiveTintColor: "#007bff",
          tabBarInactiveTintColor: "gray",
        })}
      >
        <Tab.Screen name="홈" component={HomeScreen} />
        <Tab.Screen name="주행" component={DrivingStack} />
        <Tab.Screen name="기록실" component={RecordScreen} />
        <Tab.Screen name="마이페이지" component={MyPageScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
