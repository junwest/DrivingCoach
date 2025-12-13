// navigation/DrivingStack.tsx
import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import DrivingScreen from "../screens/tabNavScreens/DrivingScreen";
import DrivingReady from "../Driving/DrivingReady";
import Driving from "../Driving/driving";

const Stack = createNativeStackNavigator();

export default function DrivingStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="DrivingScreen" component={DrivingScreen} />
      <Stack.Screen name="DrivingReady" component={DrivingReady} />
      <Stack.Screen name="Driving" component={Driving} />
    </Stack.Navigator>
  );
}
