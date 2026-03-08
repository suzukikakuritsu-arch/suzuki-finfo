# suzuki-finfo
# 鈴木F_info地震モニター

**鈴木情報創発理論 (GER理論)** に基づく地震活動方向検出システム

> 値が変わる前に方向が変わる

## 理論

```
F_info = dI_suzuki/dt
I_suzuki = P(interact) × [H(X|Y) + H(Y|X)]
閾値 = φ^(-3) = 0.2361   φ = 黄金比 = 1.6180...
```

|状態       |意味       |
|---------|---------|
|EMERGENCE|エネルギー蓄積方向|
|REFLUX   |放出・静穏化方向 |
|STABLE   |安定状態     |

## セットアップ（3ステップ）

1. このリポジトリを **Fork**
1. Settings → Pages → Source: **`docs/` フォルダ** を選択
1. Actions → 「F_info地震モニター」→ **Run workflow**

以後は毎日 JST 9:00 に自動更新されます。
手動実行もいつでも可能です。

## 標準ライブラリのみ使用

追加インストール不要。Python 3.x で動作します。

## 著作権

© 鈴木悠起也 (Suzuki Yukiya) 2026
理論: 鈴木情報創発理論 / GER理論 / 鈴木統一理論

データ: [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/)
