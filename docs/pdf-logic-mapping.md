# PDF Philosophy → Code Mapping

## 1. 차트 흐름은 이어지는 하나의 시퀀스

**PDF 핵심**: 패턴 하나가 아니라 `T바닥 → 포킹 → 펌핑 → 랠리 → 역배열재매집 → 재랠리` 흐름의 연속성이 신뢰를 결정한다.

**구현**:
- `flow_engine._classify_stage()`: 현재 단계 분류
- `flow_engine._classify_stage(tail_from=12)`: 12봉 전 단계 분류 → 전환 이력
- `flow_engine._continuity_score(current, prior)`: 자연스러운 전환 = 6점, 비정상 전환 = 2점
- `scoring_engine.finalize()`: continuity_adj (-5 ~ +2)로 최종 점수에 반영

## 2. T바닥

**PDF**: 하락 후 압축 → 도지/역망치 → 확인봉 순서, 저점 근처 거래량 수축이 중요.

**구현** (`technical_engine.detect_t_bottom`):
- 직전 60일 하락률 < -15% → 기저 충족
- `compression_ratio(tail(30)) < 0.035` → 타이트한 가격 압축
- `is_doji(last)` 또는 밑꼬리 긴 캔들 → 도지/역망치 신호
- 60일 저점 대비 8% 이내 → 저점 근접

## 3. 탑다운 테마/섹터 분석

**PDF**: 섹터 → 테마 → 종목 순서로 접근. 테마 내 선도주인지 동반 상승인지 확인.

**구현** (`theme_engine.analyze`):
- `sector_perf_1m`, `theme_perf_1m` → 섹터/테마 강도 점수
- `peer_confirmation_ratio` → 동시에 강세인 피어 비율
- `own_perf > peer_avg + 3%` → leader, 이하 → follower
- leader면 `leader_bonus` 2점 추가

## 4. 멀티 타임프레임

**PDF**: "진입은 일봉, 방향은 주·월봉". 상위 타임프레임이 부정적이면 일봉 셋업을 신뢰하지 않는다.

**구현** (`timeframe_engine.analyze`):
- `ta.resample(daily, 'W-FRI')` / `ta.resample(daily, 'ME')` → 주봉/월봉 자동 생성
- 각 프레임에 `_score_higher_frame()` 또는 `_score_daily()` 적용
- 일봉 high but 월봉/주봉 low → `buckets.daily -= 1.5` 하향 패널티

## 5. 매출 vs 영업이익 증가율 비교

**PDF**: "영업이익 증가율이 매출 증가율을 상회하는 것이 중요 신호"

**구현** (`fundamentals_engine.analyze`):
```python
if op_last - rev_last > 10:      # op >> revenue
    buckets.op_gt_revenue = 3.0  # max 3점
elif op_last > rev_last:
    buckets.op_gt_revenue = 2.0
```
- 단순 절대 수치가 아닌 **방향성과 레버리지 발현 여부** 평가

## 6. 과열 = 진입 금지

**PDF**: 과대 이격 / 급등 직후 추격 금지.

**구현** (`scoring_engine.finalize`):
- `stage == 과열` → `overheat_penalty = 15` 차감
- Action override: 과열이면 Strong Buy 불가
- `flow_engine` 과열 진입 시 `late_stage_penalty = 6.0`

## 7. 리스크 = 곱하는 게이트

**PDF**: 리스크가 높으면 아무리 좋은 차트도 진입하면 안 된다.

**구현**: 리스크 0–10점을 곱수로 변환:
```python
risk_multiplier = rescale(risk_score, 0, 10, 1.0, 0.55)
final = raw_positive × risk_multiplier - overheat_penalty
```
기존 ChatGPT 지시서의 "더하는 구조"에서 **곱하는 게이트**로 변경.
