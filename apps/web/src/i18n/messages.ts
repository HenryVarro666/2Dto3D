// Chinese source text, followed by English and Spanish. Keep placeholders identical.
export const messages = {
  退步: ["Regression", "Retroceso"],
  独立真实场景测试: [
    "Independent real-scene tests",
    "Pruebas de escenas reales independientes",
  ],
  "3个新场景 · 9张真实照片": [
    "3 new scenes · 9 real photographs",
    "3 escenas nuevas · 9 fotografías reales",
  ],
  办公室: ["Office", "Oficina"],
  卸货区: ["Delivery area", "Zona de carga"],
  材料展示走廊: ["Materials corridor", "Pasillo de materiales"],
  "未用于本项目前轮调试；不保证未进入VGGT训练。每方案12条检查线，4条跨墙线。": [
    "Unused in prior project tuning; exclusion from VGGT training is not established. Each policy: 12 held-out lines, 4 across walls.",
    "No se usaron en ajustes previos del proyecto; no se garantiza su exclusión del entrenamiento de VGGT. Cada método: 12 líneas reservadas, 4 entre paredes.",
  ],
  "激光扫描提供独立参考；每场景仅A–B标定。跨墙是两端点直线，非垂直净距；不是PV设备精度验证。":
    [
      "Independent laser references; only A–B calibrates each scene. Cross-wall means endpoint distance, not perpendicular clearance; this does not validate PV equipment accuracy.",
      "Referencia láser independiente; solo A–B calibra cada escena. Entre paredes indica distancia entre puntos, no separación perpendicular; no valida precisión en equipos fotovoltaicos.",
    ],
  "原图 RGB": ["Original RGB", "RGB original"],
  "去畸变 RGB": ["Rectified RGB", "RGB rectificado"],
  "记录缺失、失败或协议不匹配，暂不计算汇总。": [
    "Records are missing, failed or do not match the protocol; aggregates are withheld.",
    "Faltan registros, han fallado o no coinciden con el protocolo; no se calculan agregados.",
  ],
  "检查线平均误差（MAPE）": [
    "Held-out mean error (MAPE)",
    "Error medio reservado (MAPE)",
  ],
  跨墙平均误差: ["Cross-wall mean error", "Error medio entre paredes"],
  最大单线误差: ["Worst line error", "Mayor error por línea"],
  全部12条独立检查线: ["All 12 held-out lines", "Las 12 líneas reservadas"],
  真实场景: ["Real scene", "Escena real"],
  "检查线 / 参考 mm": [
    "Held-out line / reference mm",
    "Línea reservada / referencia mm",
  ],
  "校准 mm / 误差": ["Calibrated mm / error", "mm calibrados / error"],
  跨墙: ["Across walls", "Entre paredes"],
  跨表面: ["Across surfaces", "Entre superficies"],
  同一表面: ["Same surface", "Misma superficie"],
  真实照片与扫描依据: [
    "Real photographs and scan references",
    "Fotografías reales y referencias del escáner",
  ],
  "原始照片无实体标尺；参考来自另行获取的激光扫描。": [
    "No physical ruler in the photos; references come from separately acquired laser scans.",
    "Las fotos no incluyen una regla física; las referencias proceden de escaneos láser obtenidos por separado.",
  ],
  耗时与已知相机辅助检查: [
    "Timing and known-camera auxiliary checks",
    "Tiempos y controles auxiliares con cámara conocida",
  ],
  "缓存权重，M4 Pro；耗时仅含独立worker，不含上传和查看器。已知K另用A–B求比例，不混入主指标。":
    [
      "Cached weights, M4 Pro. Times cover the isolated worker, excluding upload and viewer. Known-K uses a separate A–B scale and is excluded from primary metrics.",
      "Pesos en caché, M4 Pro. Los tiempos cubren el proceso aislado, sin carga ni visor. K conocida usa una escala A–B separada y no entra en las métricas principales.",
    ],
  "逆序复跑数组、点云和长度一致；重复不增加独立样本。": [
    "Reverse-order repeats match arrays, clouds and lengths; repeats add no independent samples.",
    "La repetición en orden inverso coincide en matrices, nubes y longitudes; no añade muestras independientes.",
  ],
  "复跑存在差异或未完成，请查看完整实验报告。": [
    "Repeats differ or are incomplete; consult the full experiment report.",
    "Las repeticiones difieren o están incompletas; consulte el informe completo.",
  ],
  完整实验报告: ["Full experiment report", "Informe completo del experimento"],
  左墙纵向参照: [
    "Left-wall vertical calibration",
    "Calibración vertical de pared izquierda",
  ],
  左右墙跨墙线1: [
    "Left-to-right wall line 1",
    "Línea 1 entre paredes izquierda y derecha",
  ],
  左墙横向: ["Left-wall horizontal", "Horizontal de pared izquierda"],
  左右墙跨墙线2: [
    "Left-to-right wall line 2",
    "Línea 2 entre paredes izquierda y derecha",
  ],
  右墙纵向: ["Right-wall vertical", "Vertical de pared derecha"],
  后墙纵向参照: [
    "Back-wall vertical calibration",
    "Calibración vertical de pared trasera",
  ],
  后墙横向: ["Back-wall horizontal", "Horizontal de pared trasera"],
  近侧柱面纵向: ["Near-column vertical", "Vertical de columna cercana"],
  后墙至近侧柱面: [
    "Back wall to near column",
    "Pared trasera a columna cercana",
  ],
  后墙至拖车表面: [
    "Back wall to trailer surface",
    "Pared trasera a superficie del remolque",
  ],
  走廊左右墙跨墙线1: [
    "Corridor cross-wall line 1",
    "Línea 1 entre paredes del pasillo",
  ],
  走廊左右墙跨墙线2: [
    "Corridor cross-wall line 2",
    "Línea 2 entre paredes del pasillo",
  ],
  缩放方式同点对照: [
    "Fixed-point resize comparison",
    "Comparación de escala con puntos fijos",
  ],
  "图像条件（缩放对照）": ["Fixed RGB condition", "Condición RGB fija"],
  固定去畸变图: ["Fixed rectified RGB", "RGB rectificado fijo"],
  固定原图: ["Fixed original RGB", "RGB original fijo"],
  当前14对齐: ["Current 14-aligned resize", "Escala actual alineada a 14"],
  保比例缩放: ["Isotropic resize", "Escala isotrópica"],
  "图像条件固定；只比较缩放方式。每场景 A–B 标定，四条长度仅验证。": [
    "RGB is held fixed; only resizing changes. A–B sets scale in each scene; four lengths are held out.",
    "El RGB es fijo; solo cambia el escalado. A–B fija la escala en cada escena; cuatro longitudes se reservan para validar.",
  ],
  "当前有效内容 {width}×{height}；纵横拉伸 {stretch}%。": [
    "Current content: {width}×{height}; relative vertical stretch {stretch}%.",
    "Contenido actual: {width}×{height}; estiramiento vertical relativo del {stretch}%.",
  ],
  "保比例有效内容 {width}×{height}，存储高度 {stored}；实际取点使用连续映射。":
    [
      "Isotropic content: {width}×{height}, stored height {stored}; physical points use the continuous mapping.",
      "Contenido isotrópico: {width}×{height}, altura almacenada {stored}; los puntos físicos usan el mapeo continuo.",
    ],
  "原图与去畸变分层不混算；有效像素覆盖和白边也随缩放变化，不能单独确定深度模型的根因。":
    [
      "Original and rectified strata are kept separate. Pixel coverage and white borders also change; this does not isolate a unique depth-model cause.",
      "Los estratos original y rectificado se mantienen separados. También cambian la cobertura y los bordes blancos; esto no aísla una causa única del modelo de profundidad.",
    ],
  查看当前点云: ["Current cloud", "Nube con escala actual"],
  查看保比例点云: ["Isotropic cloud", "Nube con escala isotrópica"],
  "当前：校准长度 / 误差": [
    "Current: calibrated length / error",
    "Actual: longitud calibrada / error",
  ],
  "保比例：校准长度 / 误差": [
    "Isotropic: calibrated length / error",
    "Isotrópica: longitud calibrada / error",
  ],
  实际518输入与同点标记: [
    "Actual 518 inputs and matching physical points",
    "Entradas reales de 518 y puntos físicos coincidentes",
  ],
  "橙色 A–B 用于标定，绿色 C–J 仅验证；同名标记对应同一扫描点，按各自缩放映射取样。":
    [
      "Orange A–B sets scale; green C–J are held out. Matching labels identify the same scanner points sampled through each resize mapping.",
      "A–B en naranja fija la escala; C–J en verde solo valida. Las mismas etiquetas identifican los mismos puntos del escáner bajo cada mapeo de escala.",
    ],
  "模型输入预览来自实际准备张量；JPEG仅供查看，原始PNG和哈希保留。": [
    "Previews come from the actual prepared tensors. JPEG is for viewing; lossless PNGs and hashes are retained.",
    "Las vistas provienen de los tensores preparados reales. El JPEG es solo para visualizar; se conservan los PNG sin pérdida y los hashes.",
  ],
  跨墙与后墙深度诊断: [
    "Cross-wall and back-wall depth diagnostics",
    "Diagnóstico de profundidad entre paredes y pared trasera",
  ],
  "当前 Z（校准后）": ["Current Z (calibrated)", "Z actual (calibrada)"],
  "保比例 Z（校准后）": [
    "Isotropic Z (calibrated)",
    "Z isotrópica (calibrada)",
  ],
  "已知 K 辅助跨墙误差：当前 {before}%，保比例 {after}%；各自只用 A–B 拟合辅助比例，不计入主结果。":
    [
      "Known-K auxiliary cross-wall error: current {before}%, isotropic {after}%. Each auxiliary scale uses A–B only and is excluded from the primary comparison.",
      "Error auxiliar entre paredes con K conocida: actual {before}%, isotrópico {after}%. Cada escala auxiliar usa solo A–B y se excluye de la comparación principal.",
    ],

  同点去畸变对照: [
    "Fixed-point undistortion comparison",
    "Comparación de corrección de distorsión con puntos fijos",
  ],
  固定20个扫描参考点: [
    "20 fixed scanner reference points",
    "20 puntos fijos de referencia del escáner",
  ],
  原图输入: ["Original input", "Entrada original"],
  去畸变输入: ["Rectified input", "Entrada corregida"],
  原图点云: ["Original cloud", "Nube original"],
  去畸变点云: ["Rectified cloud", "Nube rectificada"],
  "模型、分辨率和实际参考点固定；每场景只用 A–B 标定，四条检查线不参与拟合。": [
    "Model, resolution and physical reference points are fixed. Only A–B sets scale in each scene; four check lengths are excluded from the fit.",
    "El modelo, la resolución y los puntos físicos de referencia son fijos. Solo A–B fija la escala de cada escena; las cuatro comprobaciones no intervienen en el ajuste.",
  ],
  "{better} 条改善，{worse} 条退步；复跑不增加独立样本数。": [
    "{better} checks improve and {worse} worsen; repeated runs add no independent samples.",
    "Mejoran {better} comprobaciones y empeoran {worse}; las repeticiones no añaden muestras independientes.",
  ],
  "对照条件不一致或运行未完成，暂不汇总误差。": [
    "Conditions differ or runs are incomplete; aggregate errors are withheld.",
    "Las condiciones difieren o faltan ejecuciones; no se resumen los errores.",
  ],
  "E08 使用固定扫描坐标和亚像素深度取样，已重算原图基线；请与 E07 的最近顶点结果分开阅读。":
    [
      "E08 uses fixed scan coordinates and subpixel depth sampling, with a recomputed original baseline. Read it separately from E07's nearest-vertex results.",
      "E08 usa coordenadas fijas del escáner y profundidad subpíxel, con una nueva línea base original. Distíngalo de los resultados del vértice más cercano de E07.",
    ],
  "去畸变使用数据集已知相机标定，保留源视场边界；无效白边约1.24%。相机标定是额外信息，普通现场照片未必具备。":
    [
      "Rectification uses known dataset camera calibration and preserves sampled source-field boundaries; invalid white borders occupy about 1.24%. Calibration is additional information that field photos may lack.",
      "La corrección usa la calibración de cámara del conjunto y conserva los límites muestreados del campo original; los bordes blancos no válidos ocupan aproximadamente el 1.24%. Las fotos de campo pueden carecer de esta calibración adicional.",
    ],
  "同一实际位置，前后参考长度一致": [
    "Same physical locations and identical reference lengths",
    "Mismas posiciones físicas y longitudes de referencia idénticas",
  ],
  共同扫描参考: ["Shared scan reference", "Referencia común del escáner"],
  "原图：校准长度 / 误差": [
    "Original: calibrated length / error",
    "Original: longitud calibrada / error",
  ],
  "去畸变：校准长度 / 误差": [
    "Rectified: calibrated length / error",
    "Corregida: longitud calibrada / error",
  ],
  "误差变化（百分点）": [
    "Error change (percentage points)",
    "Cambio de error (puntos porcentuales)",
  ],
  "此场景对照暂不可用。": [
    "This scene comparison is unavailable.",
    "La comparación de esta escena no está disponible.",
  ],
  同一物理点的照片对照: [
    "Photo comparison of the same physical points",
    "Comparación fotográfica de los mismos puntos físicos",
  ],
  "橙色 A–B 只用于标定，绿色 C–J 用于检查；同名标记对应同一扫描点，像素位置随去畸变映射变化。":
    [
      "Orange A–B only calibrates scale; green C–J are checks. Matching labels identify the same scan point; pixel positions change through the rectification map.",
      "A–B en naranja solo calibra la escala; C–J en verde son comprobaciones. Las etiquetas iguales corresponden al mismo punto del escáner; su posición en píxeles cambia con la corrección.",
    ],
  "本机尚无该归档照片；可先准备数据，或载入新运行的任务 ID。": [
    "The archived photo is unavailable locally. Prepare the data or load a new run's job ID.",
    "La foto archivada no está disponible localmente. Prepare los datos o cargue el ID de una nueva ejecución.",
  ],
  固定实际取点标记: [
    "Fixed physical point markers",
    "Marcadores de puntos físicos fijos",
  ],
  "固定点 {scene} {id}": [
    "Fixed point {scene} {id}",
    "Punto fijo {scene} {id}",
  ],
  "518 难例的深度诊断": [
    "Depth diagnostics for hard 518 cases",
    "Diagnóstico de profundidad de los casos difíciles a 518",
  ],
  "下列深度使用各自 A–B 比例并依赖相机估计，用于定位问题，不能单独确定根因。": [
    "These depths use each run's A–B scale and depend on camera estimates. They help locate problems, not establish a unique cause.",
    "Estas profundidades usan la escala A–B de cada ejecución y dependen de la cámara estimada. Ayudan a localizar problemas, no a establecer una causa única.",
  ],
  固定点: ["Fixed point", "Punto fijo"],
  "扫描 Z": ["Scan Z", "Z del escáner"],
  "原图 Z（校准后）": ["Original Z (calibrated)", "Z original (calibrada)"],
  "去畸变 Z（校准后）": ["Rectified Z (calibrated)", "Z corregida (calibrada)"],
  "同一预测深度使用已知内参并另用 A–B 标定后，跨墙误差仍为 {error}%；此辅助结果不计入主对照。":
    [
      "Using known intrinsics with the same predicted depths and a separate A–B scale still gives {error}% cross-wall error. This auxiliary result is excluded from the primary comparison.",
      "Con intrínsecos conocidos, las mismas profundidades y una escala A–B separada, el error entre paredes sigue siendo del {error}%. Este diagnóstico no entra en la comparación principal.",
    ],
  "点云另含明确标记的插值端点审计层，原始模型样本另存。原始 GLB / PLY 仍为相对尺度；这些结果不代表现场毫米精度。":
    [
      "The audit cloud includes an identified interpolated-endpoint layer; raw model samples are saved separately. GLB/PLY keep relative scale. These results do not establish millimeter accuracy in the field.",
      "La nube incluye una capa identificada de extremos interpolados; las muestras originales se guardan aparte. GLB/PLY conservan escala relativa. Los resultados no establecen precisión milimétrica en campo.",
    ],
  "本审计包含按固定图像位置插值的端点；原始模型样本另存。": [
    "This audit includes endpoints interpolated at fixed image positions. Raw model samples are saved separately.",
    "Esta auditoría incluye extremos interpolados en posiciones fijas de imagen. Las muestras originales se guardan aparte.",
  ],
  "只读几何审计：可查看、测距和导出记录；本次重放不执行组件识别或重建。": [
    "Read-only geometry audit: view, measure and export records. This replay does not run component recognition or reconstruction.",
    "Auditoría de geometría de solo lectura: consulte, mida y exporte registros. Esta reproducción no ejecuta reconocimiento de componentes ni reconstrucción.",
  ],
  公开尺寸验证: ["Public metric validation", "Validación métrica pública"],
  "2 个场景 · 6 张照片 · 8 条独立长度": [
    "2 scenes · 6 photos · 8 independent lengths",
    "2 escenas · 6 fotos · 8 longitudes independientes",
  ],
  "激光扫描参考；照片中没有实体标定尺。每个场景只用 A–B 标定，C–J 只用于独立检查。":
    [
      "Laser-scan reference; there is no physical ruler in the photos. Each scene uses only A–B for calibration; C–J are independent checks.",
      "Referencia de escáner láser; las fotos no incluyen una regla física. Cada escena usa solo A–B para calibrar; C–J son comprobaciones independientes.",
    ],
  平均绝对百分比误差: [
    "Mean absolute percentage error",
    "Error porcentual absoluto medio",
  ],
  "提高分辨率改善了多数检查线，但 kicker 后墙误差从 10.36% 升至 12.59%。单条标定线不能消除整体形变。":
    [
      "Higher resolution improved most checks, but the kicker back-wall error rose from 10.36% to 12.59%. One reference length cannot remove global deformation.",
      "Una mayor resolución mejoró la mayoría de las comprobaciones, pero el error de la pared posterior de kicker aumentó del 10.36% al 12.59%. Una longitud de referencia no elimina la deformación global.",
    ],
  "这是两个公开场景的小样本诊断，不代表逆变器现场精度。两种分辨率取最近输出像素，端点略有移动；桌球台因缺少扫描参考而未测量。":
    [
      "This small diagnostic on two public scenes does not establish field inverter accuracy. Endpoints move slightly when snapped to the nearest output pixel at each resolution; the foosball table was not measured because scan reference was missing.",
      "Este diagnóstico de dos escenas públicas no establece la precisión de inversores en campo. Los extremos varían ligeramente al usar el píxel de salida más cercano en cada resolución; no se midió el futbolín por falta de referencia del escáner.",
    ],
  "标定 A–B": ["Calibration A–B", "Calibración A–B"],
  模型流程: ["Model pipeline", "Proceso del modelo"],
  查看点云与测量记录: [
    "View point cloud and measurements",
    "Ver nube de puntos y mediciones",
  ],
  独立检查线: ["Independent check", "Comprobación independiente"],
  扫描参考: ["Scan reference", "Referencia del escáner"],
  校准后: ["Calibrated", "Calibrada"],
  绝对误差: ["Absolute error", "Error absoluto"],
  相对误差: ["Relative error", "Error relativo"],
  运行失败: ["Run failed", "Ejecución fallida"],
  "模型流程耗时包含每次进程加载、推理和几何写出，不含下载、上传和浏览器；不是端到端耗时。":
    [
      "Model pipeline time includes per-process loading, inference and geometry writing; it excludes downloads, uploads and the browser, so it is not end-to-end latency.",
      "El tiempo del modelo incluye carga del proceso, inferencia y escritura de geometría; excluye descargas, subidas y navegador. No es latencia de extremo a extremo.",
    ],
  "新克隆可直接查看汇总；点云重放需先运行 E07 数据准备与评测脚本。视图分组只是几何审计，不代表自动组件分割。":
    [
      "A fresh clone can show this summary. Point-cloud replay requires the E07 data preparation and evaluation script. View groups support geometry auditing, not automatic component segmentation.",
      "Un clon nuevo muestra este resumen. Para reproducir la nube se requiere el script E07 de datos y evaluación. Los grupos de vistas sirven para auditar geometría, no para segmentar componentes automáticamente.",
    ],
  原始数据与来源: ["Original data and source", "Datos originales y fuente"],
  完整结果与复现步骤: [
    "Full results and reproduction",
    "Resultados completos y reproducción",
  ],
  "柜体横向 C–D": ["Cabinet horizontal C–D", "Ancho del armario C–D"],
  "橙色面板纵向 E–F": [
    "Orange panel vertical E–F",
    "Altura del panel naranja E–F",
  ],
  "管道纵向 G–H": ["Pipe vertical G–H", "Altura de tubería G–H"],
  "柜体至管道 I–J": ["Cabinet to pipe I–J", "Armario a tubería I–J"],
  "后墙 C–D": ["Back wall C–D", "Pared posterior C–D"],
  "侧墙 E–F": ["Side wall E–F", "Pared lateral E–F"],
  "后墙至侧墙 G–H": [
    "Back wall to side wall G–H",
    "Pared posterior a lateral G–H",
  ],
  "柜体下段 I–J": ["Cabinet lower span I–J", "Tramo inferior del armario I–J"],
  "公开扫描参考验证，不代表现场尺寸精度。": [
    "Public scan reference validation does not establish field dimensional accuracy.",
    "La validación con escáner público no establece la precisión dimensional en campo.",
  ],
  "此结果按照片视图分组，用于几何审计，不代表组件识别。": [
    "This geometry audit groups points by photo view; it does not demonstrate component recognition.",
    "Esta auditoría agrupa puntos por vista fotográfica; no demuestra reconocimiento de componentes.",
  ],
  "解析测量演示未运行模型；组件细化和重建请使用真实多图结果。": [
    "This analytic measurement demo runs no models. Use a real multi-view result for refinement and reconstruction.",
    "Esta demostración analítica no ejecuta modelos. Use un resultado multivista real para refinar y reconstruir.",
  ],
  查看参照端点: ["Show reference endpoints", "Ver extremos de referencia"],
  查看端点: ["Show endpoints", "Ver extremos"],
  标定与测距: ["Calibration & measurement", "Calibración y medición"],
  "参照校准 · 几何仍为估算": [
    "Reference calibrated · Geometry remains estimated",
    "Calibrada con referencia · Geometría estimada",
  ],
  "估算几何 · 尺度未知": [
    "Estimated geometry · Scale unknown",
    "Geometría estimada · Escala desconocida",
  ],
  "一个已知长度只校准比例，不修正形变。请用另一条独立实测长度验证；结果不作为工程验收尺寸。":
    [
      "One known length calibrates scale, not shape. Check another independently measured length; these dimensions are not for engineering acceptance.",
      "Una longitud conocida calibra la escala, no la forma. Verifique otra longitud medida de forma independiente; no son dimensiones de aceptación técnica.",
    ],
  结束选点: ["Finish picking", "Terminar selección"],
  "在点云中选择 A / B": ["Pick A / B in the cloud", "Elegir A / B en la nube"],
  清除选点: ["Clear points", "Borrar puntos"],
  "已选 {count}/2 个点": [
    "{count}/2 points selected",
    "{count}/2 puntos seleccionados",
  ],
  "点击可见表面的实际点。A、B 标记和连线使用原始坐标；选点时关闭组件分解。": [
    "Click actual points on visible surfaces. A/B markers and the line use original coordinates; exploded view is disabled while picking.",
    "Pulse puntos reales de superficies visibles. A/B y la línea usan coordenadas originales; la vista explosionada se desactiva al seleccionar.",
  ],
  "相对距离：{distance} u": [
    "Relative distance: {distance} u",
    "Distancia relativa: {distance} u",
  ],
  "校准尺寸：{distance} mm": [
    "Calibrated length: {distance} mm",
    "Longitud calibrada: {distance} mm",
  ],
  测量备注: ["Measurement note", "Nota de medición"],
  已知尺寸标定: [
    "Known-length calibration",
    "Calibración con longitud conocida",
  ],
  已知长度: ["Known length", "Longitud conocida"],
  标定单位: ["Calibration unit", "Unidad de calibración"],
  "长度来源 / 端点说明": [
    "Length source / endpoints",
    "Fuente de longitud / extremos",
  ],
  "例如：卷尺测得正面 A–B；记录拍摄或实测依据": [
    "e.g. tape-measured front A–B; record the measurement evidence",
    "Ej.: A–B frontal medido con cinta; registre la evidencia",
  ],
  保存标定: ["Save calibration", "Guardar calibración"],
  两点直线距离: ["Straight-line distance", "Distancia en línea recta"],
  尺度依据: ["Scale basis", "Base de escala"],
  "未标定：仅相对单位": [
    "Uncalibrated: relative units only",
    "Sin calibrar: solo unidades relativas",
  ],
  当前参照: ["Active reference", "Referencia activa"],
  加入独立验证长度: [
    "Add a held-out length",
    "Añadir longitud de validación independiente",
  ],
  独立实测长度: [
    "Independently measured length",
    "Longitud medida independientemente",
  ],
  验证单位: ["Validation unit", "Unidad de validación"],
  验证长度来源: [
    "Validation length source",
    "Fuente de longitud de validación",
  ],
  "确认这条长度未用于标定。换点重画同一标定线仍不构成独立验证。": [
    "Confirm this length was not used for calibration. Redrawing the reference with nearby points is still not an independent check.",
    "Confirme que esta longitud no se usó para calibrar. Redibujar la referencia con puntos cercanos no es una validación independiente.",
  ],
  "保存测距 / 验证": [
    "Save distance / validation",
    "Guardar distancia / validación",
  ],
  "正在读取或保存测量记录…": [
    "Loading or saving measurement records…",
    "Leyendo o guardando mediciones…",
  ],
  重新载入记录: ["Reload records", "Recargar registros"],
  "部分记录对应旧几何，已保留但不能用于当前点云。": [
    "Some records belong to older geometry. They are retained but cannot calibrate this cloud.",
    "Algunos registros pertenecen a geometría anterior. Se conservan pero no pueden calibrar esta nube.",
  ],
  测距与验证记录: [
    "Distances & held-out checks",
    "Distancias y comprobaciones independientes",
  ],
  距离: ["Distance", "Distancia"],
  "独立验证 / 误差": [
    "Held-out validation / error",
    "Validación independiente / error",
  ],
  参照校准: ["Reference calibrated", "Calibrada con referencia"],
  相对估算: ["Relative estimate", "Estimación relativa"],
  独立验证: ["Held-out validation", "Validación independiente"],
  "原始 GLB / PLY 保持相对尺度；校准与误差保存在独立记录中。": [
    "Raw GLB / PLY stay at relative scale; calibration and errors are stored in a separate receipt.",
    "GLB / PLY conservan escala relativa; la calibración y los errores se guardan en un registro aparte.",
  ],
  导出测量记录: ["Export measurement receipt", "Exportar registro de medición"],
  "原始几何 · 相对尺度": [
    "Raw geometry · Relative scale",
    "Geometría original · Escala relativa",
  ],
  恢复已有点云任务: [
    "Restore a point-cloud job",
    "Restaurar tarea de nube de puntos",
  ],
  "多图任务 ID": ["Multi-view job ID", "ID de tarea multivista"],
  打开已有结果: ["Open saved result", "Abrir resultado guardado"],
  "任务编号仅访问本机已有结果。照片与测量数据不会自动跨机器复制。": [
    "Job IDs open results already on this service. Photos and measurement data are not automatically copied between machines.",
    "Los ID abren resultados de este servicio. Las fotos y mediciones no se copian automáticamente entre equipos.",
  ],
  "请填写有效的多图任务 ID。": [
    "Enter a valid multi-view job ID.",
    "Introduzca un ID de tarea multivista válido.",
  ],
  "标定线不能作为独立验证线。请选择另一条未参与标定的实测长度。": [
    "The calibration segment cannot be a held-out check. Select another independently measured length.",
    "El segmento de calibración no puede usarse para validación. Elija otra longitud medida independientemente.",
  ],
  "点云已变化，请重新载入结果并重新标定。": [
    "The point cloud changed. Reload the result and calibrate again.",
    "La nube cambió. Recargue el resultado y vuelva a calibrar.",
  ],
  "所选点不存在于该点云，请重新选点。": [
    "The selected point is not in this cloud. Pick again.",
    "El punto seleccionado no existe en esta nube. Seleccione de nuevo.",
  ],
  "请选择两个不同位置的点。": [
    "Select two points at different positions.",
    "Seleccione dos puntos en posiciones distintas.",
  ],
  "标定记录与当前任务或几何不匹配。": [
    "The calibration does not match this job or geometry.",
    "La calibración no corresponde a esta tarea o geometría.",
  ],
  "请填写已知长度的来源。": [
    "Provide the known length source.",
    "Indique la fuente de la longitud conocida.",
  ],
  "独立验证需要先选择有效标定。": [
    "Select a valid calibration before a held-out check.",
    "Seleccione una calibración válida antes de una comprobación independiente.",
  ],
  "测量记录未能载入，请重试。": [
    "Measurement records could not be loaded. Retry.",
    "No se pudieron cargar las mediciones. Reinténtelo.",
  ],
  "测量记录保存失败，请重试。": [
    "The measurement was not saved. Retry.",
    "No se guardó la medición. Reinténtelo.",
  ],
  "当前任务没有可测量的点云。": [
    "This job has no measurable point cloud.",
    "Esta tarea no tiene una nube medible.",
  ],
  "找不到可测量的多图任务。": [
    "The multi-view measurement job was not found.",
    "No se encontró la tarea de medición multivista.",
  ],

  "自动分割未得到框内区域，保留候选框供人工修正。": [
    "Automatic segmentation found no region inside the box. The candidate box remains for manual correction.",
    "La segmentación automática no encontró una región dentro del recuadro. Se conserva el recuadro para corregirlo manualmente.",
  ],
  从照片组开始: ["Start with a photo group", "Empiece con un grupo de fotos"],
  当前视角照片: ["Current viewpoint photo", "Foto de la vista actual"],
  "修改保留标注 ID。完成后，点击“应用校正到点云”更新三维归属。": [
    "Edits preserve observation IDs. Click “Apply corrections to cloud” to update 3D assignments.",
    "Los cambios conservan los ID de las anotaciones. Pulse «Aplicar correcciones a la nube» para actualizar las asignaciones 3D.",
  ],
  单张照片: ["Single photo", "Una foto"],
  多角度点云: ["Multi-view cloud", "Nube de múltiples vistas"],
  重建模式: ["Reconstruction mode", "Modo de reconstrucción"],
  "同一设备，多角度观察": [
    "One device, multiple viewpoints",
    "Un equipo, múltiples vistas",
  ],
  "上传 2–8 张有重叠的照片，融合可见表面并关联组件。": [
    "Upload 2–8 overlapping photos to fuse visible surfaces and associate components.",
    "Suba de 2 a 8 fotos solapadas para fusionar superficies visibles y asociar componentes.",
  ],
  选择照片组: ["Choose photo group", "Elegir grupo de fotos"],
  选择多角度照片: ["Choose multiple viewpoints", "Elegir múltiples vistas"],
  融合并识别组件: [
    "Fuse and identify components",
    "Fusionar e identificar componentes",
  ],
  "围绕静止设备拍摄：正面、左斜、右斜；保持同一焦距，让线缆和背部支架在至少两张照片中出现。":
    [
      "Photograph the stationary device from the front and both sides. Keep the same focal length; show cables and rear brackets in at least two views.",
      "Fotografíe el equipo inmóvil de frente y desde ambos lados. Mantenga la distancia focal; incluya cables y soportes traseros en al menos dos vistas.",
    ],
  "相对尺度 · 可见表面 · 需人工核对": [
    "Relative scale · Visible surfaces · Review required",
    "Escala relativa · Superficies visibles · Requiere revisión",
  ],
  照片组: ["Photo group", "Grupo de fotos"],
  "照片 {count}：{name}": ["Photo {count}: {name}", "Foto {count}: {name}"],
  "移除照片 {count}": ["Remove photo {count}", "Quitar foto {count}"],
  等待共享队列: [
    "Waiting for the shared queue",
    "Esperando la cola compartida",
  ],
  准备多图任务: ["Preparing multi-view job", "Preparando tarea multivista"],
  载入多视角模型: [
    "Loading the multi-view model",
    "Cargando el modelo multivista",
  ],
  联合估计相机与深度: [
    "Jointly estimating cameras and depth",
    "Estimando cámaras y profundidad conjuntamente",
  ],
  生成共同坐标点云: [
    "Unprojecting into shared coordinates",
    "Proyectando a coordenadas compartidas",
  ],
  逐图识别组件: [
    "Identifying components in each view",
    "Identificando componentes en cada vista",
  ],
  融合点云与组件: [
    "Fusing points and components",
    "Fusionando puntos y componentes",
  ],
  导出点云: ["Exporting the point cloud", "Exportando la nube de puntos"],
  上传照片组: ["Uploading photo group", "Subiendo grupo de fotos"],
  联合几何推理: ["Joint geometry inference", "Inferencia geométrica conjunta"],
  等待照片组: ["Waiting for photo group", "Esperando grupo de fotos"],
  点云待核对: ["Point cloud needs review", "La nube requiere revisión"],
  点云已就绪: ["Point cloud ready", "Nube de puntos lista"],
  多图任务进度: ["Multi-view task progress", "Progreso de tarea multivista"],
  多图阶段进度: ["Multi-view stage progress", "Progreso de etapas multivista"],
  "复用已生成的几何，仅更新组件归属。": [
    "Reusing existing geometry; updating component assignments.",
    "Se reutiliza la geometría y se actualizan las asignaciones de componentes.",
  ],
  "已停止等待；服务端任务可能仍在完成。": [
    "Stopped waiting; the server job may still be finishing.",
    "Se dejó de esperar; la tarea del servidor puede seguir ejecutándose.",
  ],
  融合点云: ["Fused point cloud", "Nube de puntos fusionada"],
  共同坐标中的彩色点云: [
    "Colored points in shared coordinates",
    "Puntos de color en coordenadas compartidas",
  ],
  "选择照片组后，点击“融合并识别组件”开始。": [
    "Choose a photo group, then click “Fuse and identify components”.",
    "Elija un grupo de fotos y pulse «Fusionar e identificar componentes».",
  ],
  显示背景点: ["Show background points", "Mostrar puntos de fondo"],
  点大小: ["Point size", "Tamaño de punto"],
  当前照片的组件: ["Components in this photo", "Componentes de esta foto"],
  应用校正到点云: [
    "Apply corrections to cloud",
    "Aplicar correcciones a la nube",
  ],
  关联到全局组件: [
    "Associate with global component",
    "Asociar a un componente global",
  ],
  独立为新组件: ["Separate as new component", "Separar como componente nuevo"],
  "同一物体在不同照片中的标注可关联；相邻物体请保持独立。": [
    "Associate observations of the same object across photos; keep neighboring objects separate.",
    "Asocie anotaciones del mismo objeto entre fotos; mantenga separados los objetos vecinos.",
  ],
  全局组件: ["Global components", "Componentes globales"],
  "{count} 个点": ["{count} points", "{count} puntos"],
  "{views} 处标注 · {count} 个点": [
    "{views} observations · {count} points",
    "{views} anotaciones · {count} puntos",
  ],
  "显示全局组件 {name}": [
    "Show global component {name}",
    "Mostrar componente global {name}",
  ],
  "未识别到组件时，仍可在照片中框选补充。": [
    "If no components are detected, add them by drawing boxes on the photos.",
    "Si no se detectan componentes, añádalos dibujando recuadros en las fotos.",
  ],
  "点云呈现照片中的可见表面；遮挡处和细线可能缺失，真实尺寸未知。": [
    "The cloud shows visible surfaces. Occluded areas and thin wires may be missing; real dimensions are unknown.",
    "La nube muestra superficies visibles. Pueden faltar zonas ocultas y cables finos; las dimensiones reales son desconocidas.",
  ],
  "每组最多 8 张照片。": [
    "Each group supports up to 8 photos.",
    "Cada grupo admite hasta 8 fotos.",
  ],
  "请选择同一设备的 2–8 张不同角度照片。": [
    "Choose 2–8 different viewpoints of the same device.",
    "Elija de 2 a 8 vistas distintas del mismo equipo.",
  ],
  "多图处理未完成，请重试。": [
    "Multi-view processing did not finish. Please retry.",
    "El procesamiento multivista no terminó. Reinténtelo.",
  ],
  "多图处理失败，请检查模型安装后重试，或使用单图模式。": [
    "Multi-view processing failed. Check model setup and retry, or use single-photo mode.",
    "Falló el procesamiento multivista. Revise la instalación del modelo y reinténtelo, o use una foto.",
  ],
  "请使用不同视角，不能重复上传同一张照片。": [
    "Use different viewpoints, not copies of the same photo.",
    "Use vistas diferentes, no copias de la misma foto.",
  ],
  "照片组不存在，请重新上传。": [
    "Photo group not found. Upload it again.",
    "No se encontró el grupo. Vuelva a subirlo.",
  ],
  "多图任务不存在，请重新开始。": [
    "Multi-view job not found. Start again.",
    "No se encontró la tarea multivista. Iníciela de nuevo.",
  ],
  "多图结果尚未就绪。": [
    "Multi-view result is not ready.",
    "El resultado multivista aún no está listo.",
  ],
  "关联标注的名称和类别必须一致。": [
    "Linked observations must share a name and category.",
    "Las anotaciones asociadas deben compartir nombre y categoría.",
  ],
  "自动关联仅为候选，请核对并按需合并或拆开。": [
    "Automatic associations are suggestions. Review, merge or separate them as needed.",
    "Las asociaciones automáticas son propuestas. Revise, combine o separe según corresponda.",
  ],
  "有效视角不足，请补拍清晰且有重叠的照片。": [
    "Too few valid views. Add clear, overlapping photos.",
    "Hay pocas vistas válidas. Añada fotos claras y solapadas.",
  ],
  "拍摄位置变化太小，请向侧面移动后补拍。": [
    "Too little camera movement. Move sideways and take another photo.",
    "El movimiento de cámara es insuficiente. Desplácese lateralmente y tome otra foto.",
  ],
  "视角间的几何支持较弱，请检查是否为同一静止设备并增加重叠。": [
    "Weak cross-view geometry support. Check that photos show the same stationary device and add overlap.",
    "El soporte geométrico entre vistas es débil. Verifique que sea el mismo equipo inmóvil y añada solapamiento.",
  ],
  "未识别到组件，请在照片中框选后应用校正。": [
    "No components identified. Draw boxes on photos and apply corrections.",
    "No se identificaron componentes. Dibuje recuadros y aplique las correcciones.",
  ],
  "部分组件没有有效三维点，请细化边界或补拍近照。": [
    "Some components have no valid 3D points. Refine their boundaries or add close-up views.",
    "Algunos componentes no tienen puntos 3D válidos. Refine los límites o añada primeros planos.",
  ],
  设备结构工作台: [
    "Equipment Structure Workbench",
    "Mesa de trabajo de estructuras",
  ],
  "PV Structure 工作台首页": [
    "PV Structure workspace home",
    "Inicio de PV Structure",
  ],
  设备结构实验室: ["Equipment Structure Lab", "Laboratorio de estructuras"],
  本地工作空间: ["LOCAL WORKSPACE", "ESPACIO LOCAL"],
  一期: ["Phase 1", "Fase 1"],
  工作空间: ["Workspace", "Espacio de trabajo"],
  "照片 → 组件结构": [
    "Photo → Component structure",
    "Foto → Estructura de componentes",
  ],
  组串式逆变器与外部安装结构的可交互示意: [
    "Interactive schematics of string inverters and external mounting structures",
    "Esquemas interactivos de inversores de cadena y sus estructuras de montaje externas",
  ],
  导入照片: ["Import photo", "Importar foto"],
  更换照片: ["Replace photo", "Cambiar foto"],
  选择设备照片: ["Choose equipment photo", "Elegir foto del equipo"],
  处理步骤: ["Workflow steps", "Pasos del flujo"],
  单张现场照片: ["One field photo", "Una foto de campo"],
  识别组件: ["Identify components", "Identificar componentes"],
  可见组件候选: [
    "Visible component candidates",
    "Componentes visibles propuestos",
  ],
  查看结构: ["Explore structure", "Explorar estructura"],
  独立组件示意: [
    "Individual component schematic",
    "Esquema de componentes individuales",
  ],
  "单图 · 相对尺度 · 可人工校正": [
    "Single photo · Relative scale · Editable",
    "Una foto · Escala relativa · Editable",
  ],
  三维结构: ["3D structure", "Estructura 3D"],
  "结构示意 · 比例估计": [
    "Schematic · Estimated proportions",
    "Esquema · Proporciones estimadas",
  ],
  "正在准备三维查看器…": [
    "Preparing the 3D viewer…",
    "Preparando el visor 3D…",
  ],
  正在准备组件结构: [
    "Preparing the component structure",
    "Preparando la estructura de componentes",
  ],
  在这里查看设备的组成: [
    "Explore the equipment's components here",
    "Explore aquí los componentes del equipo",
  ],
  "识别完成后，三维视图将自动载入": [
    "The 3D view will load automatically after recognition",
    "La vista 3D se cargará al terminar el reconocimiento",
  ],
  "上传照片后，旋转、选择并逐个查看组件": [
    "Upload a photo, then rotate, select and inspect each component",
    "Suba una foto y gire, seleccione e inspeccione cada componente",
  ],
  旋转: ["Rotate", "Girar"],
  选中: ["Select", "Seleccionar"],
  分解: ["Explode", "Separar"],
  尺寸未标定: ["Dimensions not calibrated", "Dimensiones sin calibrar"],
  只看此组件: ["Isolate component", "Aislar componente"],
  恢复视图: ["Reset view", "Restablecer vista"],
  线框: ["Wireframe", "Malla de alambre"],
  组件分解: ["Exploded view", "Vista explosionada"],
  组件分解程度: ["Component separation", "Separación de componentes"],
  "拖动旋转 · 右键平移 · 滚轮缩放": [
    "Drag to rotate · Right-drag to pan · Scroll to zoom",
    "Arrastre para girar · Botón derecho para desplazar · Rueda para acercar",
  ],
  组件候选: ["Component candidates", "Componentes propuestos"],
  校正待生成: ["Edits pending rebuild", "Cambios pendientes"],
  添加组件框: ["Add component box", "Añadir recuadro"],
  重新生成结构: ["Regenerate structure", "Regenerar estructura"],
  还没有组件候选: [
    "No component candidates yet",
    "Aún no hay componentes propuestos",
  ],
  "未识别到组件时，可在照片上手动框选并命名。": [
    "If nothing is recognized, draw and name component boxes on the photo.",
    "Si no se reconoce ningún componente, dibuje recuadros en la foto y asígneles un nombre.",
  ],
  "照片中的可见机柜、安装支架和线缆会列在这里。": [
    "Visible cabinets, mounting brackets and cables will appear here.",
    "Aquí aparecerán los gabinetes, soportes de montaje y cables visibles.",
  ],
  开始框选: ["Start drawing boxes", "Empezar a dibujar recuadros"],
  "模型输出为候选，请结合照片确认。分解视图用于解释组成。": [
    "Model outputs are candidates; confirm them against the photo. The exploded view explains composition.",
    "El modelo propone componentes; compruébelos con la foto. La vista explosionada explica su composición.",
  ],
  显示全部组件: ["Show all components", "Mostrar todos los componentes"],
  如何理解这个结果: [
    "Understanding this result",
    "Cómo interpretar el resultado",
  ],
  "这是基于照片的结构示意。组件厚度和背面使用简化先验，尚未标定真实尺寸。": [
    "This is a photo-based schematic. Component thickness and hidden surfaces use simplified priors; actual dimensions are not calibrated.",
    "Este esquema se basa en la foto. El espesor y las caras ocultas usan supuestos simplificados; las dimensiones reales no están calibradas.",
  ],
  "候选组件不等同于完整工程 BOM；分解位置不代表真实拆装步骤。": [
    "Component candidates are not a complete engineering BOM. Exploded positions do not define actual disassembly steps.",
    "Los componentes propuestos no constituyen una lista de materiales de ingeniería completa. Las posiciones separadas no indican un procedimiento real de desmontaje.",
  ],
  "处理说明（{count}）": [
    "Processing notes ({count})",
    "Notas del procesamiento ({count})",
  ],
  "GLB 模型": ["GLB model", "Modelo GLB"],
  "组件 JSON": ["Component JSON", "JSON de componentes"],
  本地文件与本地推理服务: [
    "Local files and local inference",
    "Archivos e inferencia locales",
  ],
  工作台: ["Workbench", "Mesa de trabajo"],
  "新组件 {count}": ["New component {count}", "Nuevo componente {count}"],
  原始照片: ["Source photo", "Foto original"],
  打开规范化原图: [
    "Open normalized source photo",
    "Abrir foto original normalizada",
  ],
  打开原图: ["Open source photo", "Abrir foto original"],
  拖入一张设备照片: [
    "Drop an equipment photo here",
    "Arrastre aquí una foto del equipo",
  ],
  "让机柜、支架和线缆尽量清晰可见": [
    "Keep the cabinet, brackets and cables clearly visible",
    "Procure que el gabinete, los soportes y los cables se vean con claridad",
  ],
  选择照片: ["Choose photo", "Elegir foto"],
  "JPEG / PNG / WebP · 最大 20MB": [
    "JPEG / PNG / WebP · Up to 20 MB",
    "JPEG / PNG / WebP · Máximo 20 MB",
  ],
  "识别可见组件，生成独立的结构示意": [
    "Identify visible components and build a component schematic",
    "Identifique componentes visibles y genere un esquema de componentes",
  ],
  待识别的组串式逆变器现场照片: [
    "Field photo of a string inverter for recognition",
    "Foto de campo de un inversor de cadena para reconocimiento",
  ],
  "照片中选择 {name}": [
    "Select {name} in photo",
    "Seleccionar {name} en la foto",
  ],
  "在照片上拖动，框出一个可见组件": [
    "Drag on the photo to outline a visible component",
    "Arrastre sobre la foto para delimitar un componente visible",
  ],
  退出框选: ["Exit box drawing", "Salir del dibujo de recuadros"],
  松开以替换照片: [
    "Release to replace the photo",
    "Suelte para cambiar la foto",
  ],
  规范化照片: ["Normalized photo", "Foto normalizada"],
  候选框: ["Candidate boxes", "Recuadros propuestos"],
  结束框选: ["Finish drawing", "Terminar dibujo"],
  "单张照片优先 · 一期支持组串式逆变器": [
    "Single photo first · Phase 1: string inverters",
    "Una foto como punto de partida · Fase 1: inversores de cadena",
  ],
  逆变器机柜: ["Inverter cabinet", "Gabinete del inversor"],
  主机外壳: ["Main housing", "Carcasa principal"],
  安装支架: ["Mounting bracket", "Soporte de montaje"],
  支撑立柱: ["Support post", "Poste de soporte"],
  "立柱 / 支撑": ["Post / support", "Poste / soporte"],
  线缆束: ["Cable bundle", "Haz de cables"],
  接线插接件: ["Electrical connector", "Conector eléctrico"],
  电缆线槽: ["Cable tray", "Canaleta de cables"],
  其他组件: ["Other component", "Otro componente"],
  可见: ["Visible", "Visible"],
  "来源 / 模型分数": ["Source / model score", "Origen / puntuación"],
  操作: ["Actions", "Acciones"],
  "显示 {name}": ["Show {name}", "Mostrar {name}"],
  "选择 {name}": ["Select {name}", "Seleccionar {name}"],
  "只看 {name}": ["Isolate {name}", "Aislar {name}"],
  "编辑 {name}": ["Edit {name}", "Editar {name}"],
  人工框选与命名: [
    "Manually outlined and named",
    "Delimitado y nombrado manualmente",
  ],
  模型匹配分数未经准确率校准: [
    "Model matching scores are not calibrated accuracy estimates",
    "Las puntuaciones del modelo no son estimaciones calibradas de precisión",
  ],
  人工标注: ["Manual annotation", "Anotación manual"],
  模型候选: ["Model candidate", "Propuesta del modelo"],
  编辑组件: ["Edit component", "Editar componente"],
  校正组件: ["Correct component", "Corregir componente"],
  关闭组件编辑: ["Close component editor", "Cerrar editor de componentes"],
  组件名称: ["Component name", "Nombre del componente"],
  组件类别: ["Component category", "Categoría del componente"],
  移除组件: ["Remove component", "Eliminar componente"],
  "结构正在生成，完成后可继续校正。": [
    "The structure is being generated. You can continue editing when it finishes.",
    "La estructura se está generando. Podrá seguir corrigiéndola cuando termine.",
  ],
  "修改保留组件 ID。完成校正后，点击“重新生成结构”应用到三维示意。": [
    "Edits preserve component IDs. Choose Regenerate structure to apply them to the 3D schematic.",
    "Los cambios conservan los ID de los componentes. Pulse Regenerar estructura para aplicarlos al esquema 3D.",
  ],
  任务已排队: ["Task queued", "Tarea en cola"],
  正在准备识别任务: ["Preparing recognition", "Preparando el reconocimiento"],
  正在应用组件校正: [
    "Applying component corrections",
    "Aplicando correcciones de componentes",
  ],
  正在载入识别模型: [
    "Loading the recognition model",
    "Cargando el modelo de reconocimiento",
  ],
  正在识别可见组件: [
    "Identifying visible components",
    "Identificando componentes visibles",
  ],
  正在载入区域分割模型: [
    "Loading the segmentation model",
    "Cargando el modelo de segmentación",
  ],
  正在提取组件区域: [
    "Extracting component regions",
    "Extrayendo regiones de componentes",
  ],
  正在构建结构示意: [
    "Building the structural schematic",
    "Construyendo el esquema estructural",
  ],
  正在导出三维组件: ["Exporting 3D components", "Exportando componentes 3D"],
  结构已就绪: ["Structure ready", "Estructura lista"],
  从一张照片开始: ["Start with a photo", "Empiece con una foto"],
  "照片上传后将自动识别，结果保留为可校正的组件候选。": [
    "Recognition starts after upload. Component candidates remain editable.",
    "El reconocimiento comienza al subir la foto. Los componentes propuestos se pueden corregir.",
  ],
  正在上传并校验照片: [
    "Uploading and validating the photo",
    "Subiendo y validando la foto",
  ],
  "正在检查格式、图像大小与方向。": [
    "Checking the format, image size and orientation.",
    "Comprobando el formato, el tamaño y la orientación de la imagen.",
  ],
  "根据校正后的组件重新构建结构，保留对应关系。": [
    "Rebuilding from corrected components while preserving their correspondence.",
    "Reconstruyendo la estructura con los componentes corregidos y conservando sus correspondencias.",
  ],
  "首次载入或下载模型可能较久，准备完成后将自动继续。": [
    "The first model load or download may take longer. Processing will continue automatically.",
    "La primera carga o descarga del modelo puede tardar más. El procesamiento continuará automáticamente.",
  ],
  "各阶段耗时随图片和设备变化，处理进度会持续更新。": [
    "Stage durations depend on the photo and hardware. Progress updates as processing continues.",
    "La duración de cada etapa depende de la foto y del equipo. El progreso se actualiza durante el procesamiento.",
  ],
  正在载入三维结构: ["Loading the 3D structure", "Cargando la estructura 3D"],
  "组件文件已生成，正在准备可旋转的视图。": [
    "Component files are ready. Preparing the rotatable view.",
    "Los archivos de componentes están listos. Preparando la vista que permite girar el modelo.",
  ],
  "结构文件已生成，查看器暂不可用": [
    "Structure files ready; viewer unavailable",
    "Archivos de estructura listos; visor no disponible",
  ],
  结构示意已就绪: ["Schematic ready", "Esquema listo"],
  "点击照片、模型或列表中的组件，可联动选中。": [
    "Select a component in the photo, model or list to highlight it across views.",
    "Seleccione un componente en la foto, el modelo o la lista para resaltarlo en todas las vistas.",
  ],
  需要人工确认组件: [
    "Component review needed",
    "Se requiere revisar los componentes",
  ],
  "本次未生成有效结构。可在照片上框出组件，再重新生成。": [
    "No usable structure was generated. Draw component boxes on the photo, then regenerate.",
    "No se generó una estructura válida. Dibuje recuadros de componentes en la foto y vuelva a generarla.",
  ],
  已停止等待此任务: [
    "Stopped waiting for this task",
    "Se ha dejado de esperar esta tarea",
  ],
  "已上传的照片仍可框选。后端任务可能继续完成。": [
    "You can still draw on the uploaded photo. The backend task may continue.",
    "Aún puede dibujar recuadros en la foto subida. La tarea del servidor puede continuar.",
  ],
  处理未完成: ["Processing did not finish", "El procesamiento no terminó"],
  "请重试，或在照片上人工框选组件。": [
    "Retry or manually outline components on the photo.",
    "Inténtelo de nuevo o delimite los componentes manualmente en la foto.",
  ],
  按阶段显示处理进度: [
    "Stage-based processing progress",
    "Progreso por etapas",
  ],
  "已用 {seconds} 秒": [
    "Elapsed {seconds} s",
    "Tiempo transcurrido: {seconds} s",
  ],
  "包含上传、推理与视图载入": [
    "Includes upload, inference and viewer loading",
    "Incluye subida, inferencia y carga del visor",
  ],
  正在持续处理: ["Processing continues", "El procesamiento continúa"],
  本次端到端用时: ["Total end-to-end time", "Tiempo total de principio a fin"],
  停止等待任务: ["Stop waiting for task", "Dejar de esperar la tarea"],
  停止等待: ["Stop waiting", "Dejar de esperar"],
  重新识别: ["Retry recognition", "Reintentar reconocimiento"],
  上传照片: ["Upload photo", "Subir foto"],
  准备模型: ["Prepare models", "Preparar modelos"],
  提取区域: ["Extract regions", "Extraer regiones"],
  构建三维: ["Build 3D", "Construir 3D"],
  载入视图: ["Load viewer", "Cargar visor"],
  应用组件校正: ["Apply corrections", "Aplicar correcciones"],
  三维结构已就绪: ["3D structure ready", "Estructura 3D lista"],
  等待上传照片: ["Waiting for a photo", "Esperando una foto"],
  "已停止于：{stage}": ["Stopped at: {stage}", "Detenido en: {stage}"],
  "待确认：{stage}": ["Review needed: {stage}", "Revisar: {stage}"],
  "当前：{stage}": ["Current: {stage}", "Actual: {stage}"],
  任务进度: ["Task progress", "Progreso de la tarea"],
  全部完成: ["All done", "Todo listo"],
  "阶段 {current} / {total}": [
    "Stage {current} / {total}",
    "Etapa {current} / {total}",
  ],
  按处理阶段更新: ["Updates by processing stage", "Se actualiza por etapas"],
  处理阶段进度: ["Processing stage progress", "Progreso de las etapas"],
  处理阶段: ["Processing stages", "Etapas del procesamiento"],
  仅候选框: ["Boxes only", "Solo recuadros"],
  等待结果: ["Awaiting result", "Esperando resultado"],
  结果未确认: ["Result unconfirmed", "Resultado sin confirmar"],
  已完成: ["Done", "Completado"],
  进行中: ["In progress", "En curso"],
  待确认: ["Needs review", "Requiere revisión"],
  已停止: ["Stopped", "Detenido"],
  待处理: ["Pending", "Pendiente"],
  模型待载入: ["Model not loaded", "Modelo sin cargar"],
  模型载入中: ["Model loading", "Cargando modelo"],
  模型下载中: ["Model downloading", "Descargando modelo"],
  模型已就绪: ["Model ready", "Modelo listo"],
  模型不可用: ["Model unavailable", "Modelo no disponible"],
  "模型不可用，请检查本地服务日志。": [
    "Model unavailable. Check local server logs.",
    "Modelo no disponible. Revise los registros del servicio local.",
  ],
  "模型状态不可用。": [
    "Model status unavailable.",
    "El estado del modelo no está disponible.",
  ],
  本地服务未连接: ["Local service disconnected", "Servicio local desconectado"],
  正在读取模型状态: [
    "Reading model status",
    "Consultando el estado del modelo",
  ],
  "模型：{state}": ["Model: {state}", "Modelo: {state}"],
  正在连接本地服务: [
    "Connecting to local service",
    "Conectando con el servicio local",
  ],
  可旋转的三维结构示意: [
    "Rotatable 3D schematic",
    "Esquema 3D que se puede girar",
  ],
  "正在载入组件结构…": [
    "Loading component structure…",
    "Cargando estructura de componentes…",
  ],
  三维视图暂不可用: ["3D view unavailable", "Vista 3D no disponible"],
  "组件列表、照片框选和文件导出仍可使用。": [
    "The component list, photo annotations and file export remain available.",
    "La lista de componentes, los recuadros y la exportación de archivos siguen disponibles.",
  ],
  "此浏览器无法使用 WebGL。请开启浏览器硬件加速，或使用支持 WebGL 的浏览器。": [
    "WebGL is unavailable in this browser. Enable hardware acceleration or use a browser that supports WebGL.",
    "WebGL no está disponible en este navegador. Active la aceleración por hardware o use un navegador compatible con WebGL.",
  ],
  "WebGL 初始化失败。请开启浏览器硬件加速后重新打开页面。": [
    "WebGL initialization failed. Enable hardware acceleration and reopen the page.",
    "No se pudo iniciar WebGL. Active la aceleración por hardware y vuelva a abrir la página.",
  ],
  "结构文件没有可显示的几何体，请重新生成。": [
    "The structure file contains no displayable geometry. Regenerate the structure.",
    "El archivo no contiene geometría que se pueda mostrar. Regenere la estructura.",
  ],
  "结构文件缺少组件标识，请重新生成。": [
    "The structure file is missing component IDs. Regenerate the structure.",
    "Faltan los ID de componentes en el archivo. Regenere la estructura.",
  ],
  "三维结构加载失败，请检查本地服务，或重新生成结构。": [
    "The 3D structure could not load. Check the local service or regenerate it.",
    "No se pudo cargar la estructura 3D. Compruebe el servicio local o vuelva a generarla.",
  ],
  "请选择 JPEG、PNG 或 WebP 图片。": [
    "Choose a JPEG, PNG or WebP photo.",
    "Elija una foto JPEG, PNG o WebP.",
  ],
  "图片超过 20MB 上限，请选择较小的图片。": [
    "The photo exceeds the 20 MB limit. Choose a smaller photo.",
    "La foto supera el límite de 20 MB. Elija una foto más pequeña.",
  ],
  "图片超过 20MB 上限": [
    "The photo exceeds the 20 MB limit.",
    "La foto supera el límite de 20 MB.",
  ],
  "图片解码失败，请换一张照片。": [
    "The photo could not be decoded. Choose another photo.",
    "No se pudo decodificar la foto. Elija otra foto.",
  ],
  "请求未完成，请重试。": [
    "The request did not finish. Please retry.",
    "La solicitud no se completó. Inténtelo de nuevo.",
  ],
  "请求未完成（{status}），请重试。": [
    "The request failed ({status}). Please retry.",
    "La solicitud falló ({status}). Inténtelo de nuevo.",
  ],
  "无法连接本地服务，请检查 API 是否已启动，再重试。": [
    "Cannot connect to the local service. Start the API and retry.",
    "No se puede conectar con el servicio local. Inicie la API y vuelva a intentarlo.",
  ],
  参数无效: ["Invalid parameters", "Parámetros no válidos"],
  "任务因服务重启而中断。可重新识别或手动框选。": [
    "The task was interrupted by a service restart. Retry recognition or draw boxes manually.",
    "La tarea se interrumpió al reiniciar el servicio. Reintente el reconocimiento o dibuje recuadros manualmente.",
  ],
  "识别未完成，可重试或手动框选组件。": [
    "Recognition did not finish. Retry or outline components manually.",
    "El reconocimiento no terminó. Inténtelo de nuevo o delimite los componentes manualmente.",
  ],
  "模型加载或推理失败，请检查模型依赖、权重网络和设备配置。": [
    "Model loading or inference failed. Check model dependencies, weight access and device settings.",
    "Falló la carga o la inferencia del modelo. Compruebe las dependencias, el acceso a los pesos y la configuración del equipo.",
  ],
  "图片格式或内容无效，请选择 JPEG、PNG 或 WebP 图片。": [
    "The photo format or contents are invalid. Choose a JPEG, PNG or WebP photo.",
    "El formato o el contenido de la foto no es válido. Elija una foto JPEG, PNG o WebP.",
  ],
  "图片解码后尺寸过大，请选择较小图片。": [
    "The decoded image is too large. Choose a smaller photo.",
    "La imagen decodificada es demasiado grande. Elija una foto más pequeña.",
  ],
  "处理队列已满，请等当前任务完成后重试。": [
    "The processing queue is full. Retry after a task finishes.",
    "La cola está llena. Inténtelo de nuevo cuando termine una tarea.",
  ],
  "服务正在关闭，请在重启后重试。": [
    "The service is shutting down. Retry after it restarts.",
    "El servicio se está cerrando. Inténtelo de nuevo cuando se reinicie.",
  ],
  "推理服务正忙于较长任务，请稍后再试边界细化。": [
    "The inference worker is busy with a long task. Retry the refinement later.",
    "El servicio de inferencia está ocupado con una tarea larga. Reintente el refinado más tarde.",
  ],
  "边界细化文件不可用，请重新细化。": [
    "The refinement mask file is unavailable. Refine again.",
    "El archivo de la máscara no está disponible. Vuelva a refinar.",
  ],
  "32位任务ID": ["32-character job ID", "ID de tarea de 32 caracteres"],
  此服务需要访问令牌: [
    "This service requires an access token",
    "Este servicio requiere un token de acceso",
  ],
  "输入 PV3D_API_TOKEN": ["Enter PV3D_API_TOKEN", "Introduzca PV3D_API_TOKEN"],
  登录: ["Sign in", "Iniciar sesión"],
  退出登录: ["Sign out", "Cerrar sesión"],
  已通过访问令牌登录: [
    "Signed in with the access token",
    "Sesión iniciada con el token de acceso",
  ],
  "访问令牌无效，请检查后重试。": [
    "The access token is not valid. Check it and try again.",
    "El token de acceso no es válido. Compruébelo e inténtelo de nuevo.",
  ],
  "需要访问令牌才能使用本地服务。": [
    "An access token is required to use the local service.",
    "Se necesita un token de acceso para usar el servicio local.",
  ],
  "处理失败，请检查本地服务日志，重试或手动框选组件。": [
    "Processing failed. Check the local server logs, retry or outline components manually.",
    "El procesamiento falló. Revise los registros del servicio local, reinténtelo o delimite los componentes manualmente.",
  ],
  "找不到照片。": ["Photo not found.", "No se encontró la foto."],
  "找不到任务。": ["Task not found.", "No se encontró la tarea."],
  "任务尚无已完成的结果。": [
    "The task has no completed result yet.",
    "La tarea aún no tiene un resultado completo.",
  ],
  "照片文件不可用，请重新上传。": [
    "The photo file is unavailable. Upload it again.",
    "El archivo de la foto no está disponible. Vuelva a subirlo.",
  ],
  "校正必须基于同一照片的任务。": [
    "Corrections must refer to a task for the same photo.",
    "Las correcciones deben basarse en una tarea de la misma foto.",
  ],
  "结果文件不可用，请新建任务。": [
    "The result file is unavailable. Start a new task.",
    "El archivo de resultados no está disponible. Inicie una tarea nueva.",
  ],
  "没有组件场景，请手动添加或校正组件。": [
    "There is no component scene. Add or correct components manually.",
    "No hay una escena de componentes. Añada o corrija los componentes manualmente.",
  ],
  "找不到 API 路由。": [
    "API route not found.",
    "No se encontró la ruta de la API.",
  ],
  "所有几何均采用相对显示单位，真实尺度未知。": [
    "Metric scale is unknown; all geometry uses relative display units.",
    "Se desconoce la escala real; toda la geometría usa unidades de visualización relativas.",
  ],
  "深度与隐藏面来自类别先验，并非恢复的实测数据。": [
    "Depth and hidden surfaces use category priors, not recovered measurements.",
    "La profundidad y las caras ocultas usan supuestos por categoría, no medidas recuperadas.",
  ],
  "分解视图用于解释可见组成，不代表经过验证的拆装流程。": [
    "An exploded view explains visible component composition, not a verified disassembly procedure.",
    "La vista explosionada explica la composición visible, no un procedimiento de desmontaje verificado.",
  ],
  "未识别到有效组件，请手动添加或校正候选框。": [
    "No usable components were recognized. Add or correct boxes manually.",
    "No se reconocieron componentes válidos. Añada o corrija los recuadros manualmente.",
  ],
  "已从柜体示意中排除过大或过远的未知候选。": [
    "An oversized or distant unknown detection was excluded from the cabinet schematic.",
    "Se excluyó del esquema del gabinete una detección desconocida demasiado grande o alejada.",
  ],
  "已应用人工校正，未修改组件保留原有识别依据。": [
    "Manual edits were applied. Unchanged component evidence is retained from the base result.",
    "Se aplicaron los cambios manuales. Los componentes sin modificar conservan la evidencia del resultado base.",
  ],
  "MPS 推理已回退到 CPU。": [
    "MPS inference fell back to CPU.",
    "La inferencia MPS pasó a ejecutarse en la CPU.",
  ],
  "SAM 2 不可用，保留真实检测框，不使用伪造区域。": [
    "SAM 2 is unavailable. Real detection boxes are retained without fabricated regions.",
    "SAM 2 no está disponible. Se conservan los recuadros reales sin inventar regiones.",
  ],
  自动识别范围: ["Recognition scope", "Alcance del reconocimiento"],
  单设备: ["Single equipment", "Un equipo"],
  多设备: ["Multiple equipment", "Varios equipos"],
  "仅影响下一次自动识别；手工补录不受主柜数量限制。": [
    "Applies to the next recognition. Manual additions are not limited to one cabinet.",
    "Se aplica al próximo reconocimiento. Las adiciones manuales no se limitan a un gabinete.",
  ],
  按当前范围重新识别: [
    "Recognize with selected scope",
    "Reconocer con el alcance elegido",
  ],
  边界细化草稿: [
    "Boundary refinement draft",
    "Borrador de refinamiento del contorno",
  ],
  确认后加入组件: [
    "Confirm to apply the component",
    "Confirme para aplicar el componente",
  ],
  取消边界细化: [
    "Cancel boundary refinement",
    "Cancelar refinamiento del contorno",
  ],
  补录组件名称: ["Draft component name", "Nombre del componente del borrador"],
  补录组件类别: [
    "Draft component category",
    "Categoría del componente del borrador",
  ],
  修正点类型: ["Correction point type", "Tipo de punto de corrección"],
  保留物体: ["Keep object", "Conservar objeto"],
  排除背景: ["Exclude background", "Excluir fondo"],
  撤销一点: ["Undo last point", "Deshacer último punto"],
  清空点: ["Clear points", "Borrar puntos"],
  重新框选: ["Redraw box", "Volver a dibujar el recuadro"],
  "在左侧照片点击补点：绿色加号保留物体，红色减号排除背景。": [
    "Click on the photo: green plus points keep the object; red minus points exclude background.",
    "Haga clic en la foto: los puntos verdes con signo más conservan el objeto; los rojos con signo menos excluyen el fondo.",
  ],
  "正在等待或细化边界…": [
    "Waiting for or refining the boundary…",
    "Esperando o refinando el contorno…",
  ],
  "边界预览已更新，请确认是否覆盖目标物体。": [
    "Boundary preview updated. Check that it covers the intended object.",
    "Vista previa actualizada. Compruebe que cubra el objeto deseado.",
  ],
  "细化失败也可保留原框；厚度仍为估计。": [
    "You can keep the box if refinement fails. Depth remains estimated.",
    "Puede conservar el recuadro si falla el refinamiento. La profundidad sigue siendo estimada.",
  ],
  重试细化: ["Retry refinement", "Reintentar refinamiento"],
  仅用框保存: ["Save box only", "Guardar solo el recuadro"],
  确认区域: ["Confirm region", "Confirmar región"],
  细化边界: ["Refine boundary", "Refinar contorno"],
  "边界细化未完成，请重试或仅用框保存。": [
    "Boundary refinement did not finish. Retry or save the box only.",
    "El refinamiento no terminó. Reinténtelo o guarde solo el recuadro.",
  ],
  "最多添加 64 个修正点，请撤销或清空后继续。": [
    "Up to 64 correction points are allowed. Undo or clear points to continue.",
    "Se permiten hasta 64 puntos de corrección. Deshaga o borre puntos para continuar.",
  ],
  "保留点请点击框内物体；排除点可以点击背景。": [
    "Place keep points on the object inside the box. Exclude points may be on background.",
    "Coloque los puntos de conservación en el objeto dentro del recuadro. Los puntos de exclusión pueden estar en el fondo.",
  ],
  "未得到有效区域，请补点、重新框选或仅用框保存。": [
    "No usable region. Add points, redraw the box, or use the box without refinement.",
    "No se obtuvo una región válida. Añada puntos, vuelva a dibujar el recuadro o guarde solo el recuadro.",
  ],
  "边界细化失败，请重试或仅用框保存。": [
    "Boundary refinement failed. Retry or keep the box without refinement.",
    "Falló el refinamiento del contorno. Reinténtelo o conserve solo el recuadro.",
  ],
  "区域记录与当前照片或组件框不匹配，请重新细化。": [
    "The region does not match the photo or component box. Refine it again.",
    "La región no corresponde a la foto o al recuadro. Vuelva a refinarla.",
  ],
  "找不到边界细化记录，请重新细化。": [
    "Refinement not found. Refine the boundary again.",
    "No se encontró el refinamiento. Vuelva a refinar el contorno.",
  ],
  "部分修正点未被满足，请补点或重新框选。": [
    "Some prompt points were not satisfied. Add points or redraw the box.",
    "No se cumplieron algunos puntos de corrección. Añada puntos o vuelva a dibujar el recuadro.",
  ],
} as const satisfies Record<string, readonly [string, string]>;

export type MessageKey = keyof typeof messages;
