"""Render authored, editable SVG README diagrams with the Python standard library."""
import argparse
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets"


def text(x, y, value, size=16, color="#244a45", weight=400, anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>'


def box(x, y, w, h, fill="#fff", stroke="#d7e3da", radius=14):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


def arrow(x1, y1, x2, y2, color="#72a18b"):
    return f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="2" marker-end="url(#arrow)"/>'


def svg(title, description, body, h):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="{h}" viewBox="0 0 1120 {h}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="#72a18b"/></marker></defs>
<rect width="1120" height="{h}" rx="20" fill="#f4f7f1"/>
<g font-family="-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans CJK SC',sans-serif">{body}</g></svg>\n'''


def workflow(zh):
    title = "从照片到有依据的尺寸" if zh else "From photos to traceable dimensions"
    labels = [("01", "同一设备 · 2–8 个视角", "重叠、清晰、设备保持静止", "输入与照片 SHA256"),
              ("02", "联合几何 + 组件区域", "VGGT · Grounding DINO · SAM", "相机、深度、逐图观察"),
              ("03", "彩色点云与人工校正", "全局组件 ID · 原始坐标", "选择、隔离、修正、导出"),
              ("04", "参照标定与独立验证", "已知长度 → 比例 → 两点距离", "记录来源、绝对 / 相对误差")] if zh else [
              ("01", "One device · 2–8 views", "Overlap, sharpness, stationary scene", "Inputs & photo SHA256"),
              ("02", "Joint geometry + masks", "VGGT · Grounding DINO · SAM", "Cameras, depth & observations"),
              ("03", "Cloud & human correction", "Global component IDs · Raw frame", "Select, isolate, correct, export"),
              ("04", "Calibrate & validate", "Known length → scale → distance", "Sources & absolute / relative error")]
    body = text(32, 45, title, 25, weight=650)
    body += text(32, 73, "当前实现 · 全部本地运行" if zh else "Implemented · Local processing", 13, "#678077")
    for i, (number, heading, line1, line2) in enumerate(labels):
        x = 28 + i * 274
        body += box(x, 106, 246, 173)
        body += text(x+18, 138, number, 14, "#21836c", 650)
        body += text(x+18, 173, heading, 17, weight=650)
        body += text(x+18, 213, line1, 12)
        body += text(x+18, 248, line2, 12, "#678077")
        if i < 3: body += arrow(x+250, 191, x+268, 191)
    body += box(28, 301, 1066, 44, "#e4efe6", stroke="none", radius=8)
    body += text(48, 328, "单图保留结构示意；校准只改变比例，不能恢复遮挡或修正形变。" if zh else "Single-photo schematics remain available. Scale calibration cannot recover hidden surfaces or repair shape distortion.", 14)
    return svg(title, "Workflow showing multi-view input, local models, component cloud and scale validation", body, 369)


def architecture(zh):
    title = "系统架构与证据流" if zh else "Architecture & evidence flow"
    body = text(32, 45, title, 25, weight=650)
    def card(x, y, w, h, heading, lines, fill="#fff"):
        b = box(x, y, w, h, fill) + text(x+20, y+33, heading, 18, weight=650)
        for i, line in enumerate(lines): b += text(x+20, y+65+i*25, line, 13, "#59756a")
        return b
    body += card(28, 83, 290, 165, "网页 / Web" if zh else "Web workbench", ["React · TypeScript · Three.js", "照片、标注、组件与原坐标选点" if zh else "Photos, edits, components & raw picks", "中文 / English / Español"])
    body += card(400, 83, 320, 165, "本地 API / Local API" if zh else "Local API", ["FastAPI · Pydantic", "任务 / 单推理队列 / 不可变记录" if zh else "Jobs, one inference queue & receipts", "测量直接读 GLB，无需模型推理" if zh else "Measurements read GLB; no inference"])
    body += card(803, 83, 290, 165, "持久证据 / Storage" if zh else "Durable evidence", ["SQLite + local files", "照片哈希 / 版本 / 点索引 / 坐标" if zh else "Hashes, versions, indices & coordinates", "GLB / PLY / JSON + 误差记录" if zh else "GLB / PLY / JSON + error receipts"])
    body += arrow(323, 165, 390, 165) + arrow(725, 165, 793, 165)
    body += card(28, 300, 510, 140, "视觉识别与分割" if zh else "Perception models", ["Grounding DINO tiny + SAM 2.1 tiny", "单图示意 / 多图逐帧识别 / 人工区域细化" if zh else "Single schematics, per-view recognition & mask refinement"], "#e9f1e9")
    body += card(585, 300, 508, 140, "隔离的多视图 worker" if zh else "Isolated multi-view worker", ["VGGT-1B · separate Python / NumPy 1.x lock", "联合相机 + 深度 → 同一坐标系 → 组件感知融合" if zh else "Joint cameras & depth → shared frame → component-aware fusion"], "#e9f1e9")
    body += arrow(505, 253, 283, 289) + arrow(614, 253, 839, 289)
    body += text(32, 478, "模型任务共用一个有界执行器；原始数据不入 Git；无需外部推理 API。" if zh else "All model jobs share one bounded executor. Raw data stay out of Git. No external inference API.", 13, "#678077")
    return svg(title, "Local web, API and storage above bounded perception queue and isolated geometry worker", body, 505)


def scale(zh):
    title = "比例校准成功，也需要独立检查形状" if zh else "Correct scale still needs an independent shape check"
    body = text(32, 45, title, 25, weight=650)
    body += box(28, 78, 484, 286) + box(536, 78, 558, 286)
    body += text(50, 112, "标定参照 A–B" if zh else "Calibration reference A–B", 18, weight=650)
    body += '<path d="M110,160 L355,160 L355,275 L110,275 Z" fill="#e1ede5" stroke="#79a68d" stroke-width="2"/>'
    body += '<circle cx="110" cy="275" r="6" fill="#b9892d"/><circle cx="355" cy="275" r="6" fill="#b9892d"/>'
    body += text(101, 264, "A", 14) + text(348, 264, "B", 14)
    body += text(232, 198, "2.0000 u = 200 mm", 20, anchor="middle", weight=600)
    body += text(232, 231, "s = 200 / 2 = 100 mm/u", 17, anchor="middle")
    body += text(50, 337, "只有 A–B 参与求比例" if zh else "Only A–B determines the scale", 14, "#678077")
    body += text(560, 112, "未参与标定的长度" if zh else "Lengths held out from calibration", 18, weight=650)
    body += text(560, 153, "C–D", 15, weight=650) + text(634, 153, "3.3 u × 100 = 330 mm", 19)
    body += text(634, 184, "独立依据 300 mm → 误差 30 mm / 10%" if zh else "Independent truth 300 mm → error 30 mm / 10%", 15, "#986a23")
    body += text(560, 231, "E–F", 15, weight=650) + text(634, 231, "1.2 u × 100 = 120 mm", 19)
    body += text(634, 262, "独立依据 120 mm → 误差约 0" if zh else "Independent truth 120 mm → error ≈ 0", 15, "#21836c")
    body += text(560, 337, "刻意构造的非均匀形变；不是现场精度结果。" if zh else "Deliberately distorted analytic geometry; not field accuracy.", 14, "#678077")
    return svg(title, "Analytic example: one calibrated reference and two held-out checks; a ten percent height distortion remains", body, 390)


def metric(zh):
    data = json.loads((ROOT / "docs/measurement/public-metric-results.json").read_text())
    by_size = {n: [c for run in data["runs"] if run["input_size"] == n for c in run["checks"]]
               for n in [336, 518]}
    title = "公开实景测距：更高分辨率改善多数误差，仍有退步" if zh else "Public-photo measurements: higher resolution helps, with a regression"
    body = text(32, 45, title, 25, weight=650)
    body += text(32, 75, "ETH3D · 两场景 · 八条未参与标定的长度 · 每个场景只用一条长度定比例" if zh else
                 "ETH3D · Two scenes · Eight held-out lengths · One calibration length per scene", 14, "#59756a")
    for j, n in enumerate([336, 518]):
        mean = sum(c["relative_error_pct"] for c in by_size[n]) / len(by_size[n])
        body += text(32+j*340, 110, f"{n} px · {'平均绝对百分比误差' if zh else 'MAPE'} {mean:.2f}%", 16)
    for tick in range(0, 51, 10):
        x = 336+tick*13
        body += f'<path d="M{x},143 V490" stroke="#dce5dd"/>'
        body += text(x, 137, f"{tick}%", 12, "#678077", anchor="middle")
    row_names = ["pipes · 柜体横向 C–D", "pipes · 橙色面板 E–F", "pipes · 管道纵向 G–H", "pipes · 柜体至管道 I–J",
                 "kicker · 后墙 C–D", "kicker · 侧墙 E–F", "kicker · 后墙至侧墙 G–H", "kicker · 柜体下段 I–J"]
    for i, check in enumerate(by_size[336]):
        y = 158+i*42
        body += text(32, y+15, row_names[i] if zh else ("pipes · " if i < 4 else "kicker · ")+check["label"], 14)
        for j, (n, color) in enumerate([(336, "#bd8a48"), (518, "#247e6b")]):
            value = by_size[n][i]["relative_error_pct"]
            body += f'<rect x="336" y="{y+j*13}" width="{value*13:.2f}" height="9" rx="3" fill="{color}"/>'
            body += text(342+value*13, y+9+j*13, f"{value:.2f}%", 12, color)
    body += box(815, 93, 13, 10, "#bd8a48", "none", 2) + text(835, 104, "336 px", 12)
    body += box(920, 93, 13, 10, "#247e6b", "none", 2) + text(940, 104, "518 px", 12)
    body += text(32, 529, "参考来自激光扫描；照片没有实体尺。518 的 kicker 后墙仍有 12.59% 误差。" if zh else
                 "References come from laser scans; no physical ruler is visible. The 518 px back-wall error is still 12.59%.", 13, "#986a23")
    body += text(32, 557, "两种分辨率端点略有移动（最多 22.8 mm）；小样本诊断，不代表现场逆变器精度。" if zh else
                 "Pixel-snapped endpoints move by up to 22.8 mm between resolutions. This small diagnostic is not field certification.", 13, "#59756a")
    return svg(title, "Measured held-out percentage errors from frozen E07 JSON. Orange:336px; green:518px.", body, 586)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, generator in [("workflow", workflow), ("architecture", architecture), ("scale-validation", scale),
                            ("public-metric-errors", metric)]:
        for lang in ["zh", "en"]:
            path = ASSETS / f"{name}.{lang}.svg"
            expected = generator(lang == "zh")
            if args.check:
                if not path.exists() or path.read_text() != expected:
                    raise SystemExit(f"Outdated diagram: {path}")
            else: path.write_text(expected, encoding="utf-8")
    print("8 SVG diagrams verified" if args.check else "8 SVG diagrams rendered")


if __name__ == "__main__":
    main()
