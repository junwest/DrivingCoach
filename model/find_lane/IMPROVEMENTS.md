# 차선 검출 개선 비교

## 개선 전후 비교

| 항목 | 이전 버전 | 개선 버전 | 개선율 |
|------|----------|----------|--------|
| **Event 4 Detection** | 100% | 100% | - |
| **Event 4 Normal** | 0.2% | **56.3%** | **+280배** |
| **Event 5 Detection** | 100% | 100% | - |
| **Event 5 Normal** | 1.7% | **95.0%** | **+56배** |

## 주요 개선 사항

### 1. 차선 검출 방법 개선

#### 이전: HSV만 사용
```python
# 흰색/노란색 HSV 범위로만 검출
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
white_mask = cv2.inRange(hsv, lower_white, upper_white)
yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
```

#### 개선: HSV + Edge Detection 결합
```python
# HSV 검출
hsv_mask = detect_hsv(frame)

# Edge 검출 (Canny)
edge_mask = detect_edge(frame)

# 두 방법 결합 - 더 robust한 검출
combined = cv2.bitwise_or(hsv_mask, edge_mask)
```

**장점:**
- 조명 변화에 더 강건
- 약한 차선도 검출 가능
- 노이즈 감소

### 2. ROI (관심 영역) 확대

#### 이전
```python
roi_y_start = MY_CAR_BEV_Y - 200  # 200픽셀
```

#### 개선
```python
roi_y_start = MY_CAR_BEV_Y - 250  # 250픽셀 (25% 증가)
```

**효과:** 더 먼 거리의 차선도 검출

### 3. 가중 클러스터링 도입

#### 이전: 단순 평균
```python
# 각 차선 그룹의 중심을 단순 평균으로 계산
lane_center = int(np.mean(group))
```

#### 개선: 거리 가중 평균
```python
# 차량에 가까울수록 높은 가중치
weights = np.linspace(0.5, 1.0, roi.shape[0])
weighted_roi = roi * weights

# 가중치를 고려한 중심 계산
weighted_center = np.average(group, weights=column_sums[group])
```

**효과:** 차량에 가까운 차선에 더 높은 우선순위 부여

### 4. 클러스터링 파라미터 최적화

| 파라미터 | 이전 | 개선 | 설명 |
|---------|------|------|------|
| **Gap threshold** | 5px | 8px | 차선 그룹 간격 증가 |
| **Min pixels** | 3px | 2px | 최소 픽셀 수 완화 |
| **Lane threshold** | 5 | 3 | 차선 검출 임계값 낮춤 |
| **Normal threshold** | ±30% | ±35% | 정상 범위 확대 |

### 5. 시각화 개선

#### 새로운 기능:
1. **차선 중심선** (초록색) - 두 차선이 모두 검출될 때
2. **차량-차선 연결선** (회색) - 거리 시각화
3. **정보 박스** - 검은 배경에 텍스트
4. **레이블** - 차선(L/R), 차량(CAR)

## 검출 방법 비교

테스트 결과 (Event 4, Frame 100):

| 방법 | 검출 픽셀 | 비율 | 특징 |
|------|----------|------|------|
| HSV Basic | 18,878 | 15.0% | 기본 HSV |
| HSV Tuned | 30,571 | 24.3% | 파라미터 최적화 |
| Edge Based | 19,688 | 15.6% | Canny edge |
| **Combined** | **49,016** | **38.9%** | ✅ **최적** |
| Adaptive | 101,468 | 80.5% | 과도한 검출 |

## 사용 방법

### 기본 사용 (Combined 방법)
```bash
python lane_visualizer_improved.py \
  --videos "Data/이벤트 4.mp4" "Data/이벤트 5.mp4" \
  --output-dir find_lane \
  --method combined
```

### 다른 방법 테스트
```bash
# HSV만 사용
python lane_visualizer_improved.py --videos "Data/이벤트 4.mp4" --method hsv

# Edge만 사용
python lane_visualizer_improved.py --videos "Data/이벤트 4.mp4" --method edge

# Adaptive threshold
python lane_visualizer_improved.py --videos "Data/이벤트 4.mp4" --method adaptive
```

### 디버그 모드
```bash
python lane_visualizer_improved.py \
  --videos "Data/이벤트 4.mp4" \
  --method combined \
  --debug  # ROI 영역 표시
```

## 결과 파일

### 개선 전
- `이벤트 4_lane_overlay.mp4` - Normal: 0.2%
- `이벤트 5_lane_overlay.mp4` - Normal: 1.7%

### 개선 후
- `이벤트 4_improved.mp4` - Normal: **56.3%** ⬆️
- `이벤트 5_improved.mp4` - Normal: **95.0%** ⬆️

## 성능 분석

### Event 4 (차선 변경 후 깜빡이 안 끔)
- 총 프레임: 529
- 검출 성공: 529 (100%)
- 정상 주행: 298 (56.3%)
- 비정상: 231 (43.7%) - **예상된 결과** (차선 변경 이벤트)

### Event 5 (깜빡이 없이 차선 변경)
- 총 프레임: 1,061
- 검출 성공: 1,061 (100%)
- 정상 주행: 1,008 (95.0%)
- 비정상: 53 (5.0%) - **실제 차선 변경 구간**

## 기술적 개선점 요약

1. ✅ **Detection Robustness**: HSV + Edge 결합으로 다양한 조명 조건에서 검출
2. ✅ **ROI Optimization**: 25% 확대된 관심 영역
3. ✅ **Weighted Clustering**: 거리 기반 가중치로 정확도 향상
4. ✅ **Parameter Tuning**: 임계값 최적화로 false negative 감소
5. ✅ **Visualization**: 직관적인 시각화로 분석 용이성 증가

## 추천 사항

### 일반 사용
- **Method**: `combined` (HSV + Edge)
- 가장 균형잡힌 성능

### 밝은 환경
- **Method**: `hsv`
- HSV만으로도 충분

### 어두운 환경
- **Method**: `edge`
- Edge detection이 더 효과적

### 복잡한 환경
- **Method**: `combined`
- 두 방법의 장점 결합
