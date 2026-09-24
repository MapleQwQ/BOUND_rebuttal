-- 报告层可复现数据快照。数值来自 relevance_metrics_by_model_fold.json
-- 与 final_blind_interannotator_agreement.json；原始转换脚本为 analyze_final_e1.py。

WITH model_summary(model, base_adequacy, bound_adequacy, delta_adequacy, ci_low, ci_high,
                   base_slot, bound_slot, base_empty, bound_empty) AS (
  VALUES
    ('DeepSeekCoder', 0.4000, 0.2500, -0.1500, -0.3000, -0.0125, 0.5541666667, 0.4468750000, 0.0000, 0.1000),
    ('Llama-3.1',     0.4000, 0.2500, -0.1500, -0.3500,  0.0500, 0.5416666667, 0.3437500000, 0.0000, 0.0875),
    ('Qwen3',         0.3000, 0.2625, -0.0375, -0.1625,  0.0500, 0.4333333333, 0.3416666667, 0.0500, 0.1875),
    ('三模型macro',  0.3666666667, 0.2541666667, -0.1125, -0.2083333333, -0.0248958333,
                       0.5097222222, 0.3774305556, 0.0166666667, 0.1250)
)
SELECT * FROM model_summary;

WITH agreement(dimension, unit_name, exact_agreement, cohens_kappa, disagreements) AS (
  VALUES
    ('Adequacy', '回答 / 300', 0.8933, 0.834, 32),
    ('Registry status', '候选 / 960', 0.9844, 0.955, 15),
    ('Task role', '候选 / 960', 0.7177, 0.569, 271),
    ('回答slot集合', '回答 / 300', 0.8933, 0.863, 32),
    ('回答-slot二元覆盖', '回答-slot / 525', 0.9333, 0.867, 35)
)
SELECT * FROM agreement;
