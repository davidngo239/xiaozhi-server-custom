import zhCN from './zh_CN';
import vi from './vi';

// Chỉ sử dụng tùy chọn này cho nhãn và thông báo hệ thống, không bao giờ sử dụng cho nội dung người dùng hoặc giá trị API.
const labels = {
  '中文': 'Tiếng Trung', '中文普通话': 'Tiếng Trung phổ thông', '英语': 'Tiếng Anh',
  '日语': 'Tiếng Nhật', '韩语': 'Tiếng Hàn', '粤语': 'Tiếng Quảng Đông', '越南语': 'Tiếng Việt',
  '普通话': 'Tiếng Trung phổ thông', '国语': 'Tiếng Trung phổ thông',
  '法语': 'Tiếng Pháp', '德语': 'Tiếng Đức', '西班牙语': 'Tiếng Tây Ban Nha',
  '俄语': 'Tiếng Nga', '多语言': 'Đa ngôn ngữ',
  '无意图识别': 'Không nhận diện ý định', 'LLM意图识别': 'Nhận diện ý định bằng LLM',
  '函数调用意图识别': 'Nhận diện ý định qua gọi hàm', '无记忆': 'Không lưu bộ nhớ',
  '本地短记忆': 'Bộ nhớ ngắn hạn cục bộ', '仅上报聊天记录': 'Chỉ gửi lịch sử trò chuyện',
  'Mem0AI记忆': 'Bộ nhớ Mem0AI', 'PowerMem记忆': 'Bộ nhớ PowerMem',
  'SileroVAD语音活动检测': 'Phát hiện hoạt động giọng nói SileroVAD',
  'FunASR服务语音识别': 'Dịch vụ nhận dạng giọng nói FunASR',
  'FunASR语音识别': 'Nhận dạng giọng nói FunASR', 'SherpaASR语音识别': 'Nhận dạng giọng nói SherpaASR',
  'OpenAI语音识别': 'Nhận dạng giọng nói OpenAI', 'VOSK离线语音识别': 'Nhận dạng giọng nói ngoại tuyến VOSK',
  'Qwen3-ASR-Flash语音识别': 'Nhận dạng giọng nói Qwen3-ASR-Flash',
  '火山引擎语音识别': 'Nhận dạng giọng nói Volcengine',
  '火山引擎语音识别(流式)': 'Nhận dạng giọng nói liên tục Volcengine',
  '火山引擎LLM': 'LLM Volcengine', '火山引擎TTS': 'TTS Volcengine',
  '火山双流式语音合成': 'Tổng hợp giọng nói hai luồng Volcengine',
  '百度语音识别': 'Nhận dạng giọng nói Baidu', '腾讯语音识别': 'Nhận dạng giọng nói Tencent',
  '腾讯语音合成': 'Tổng hợp giọng nói Tencent', '硅基流动TTS': 'TTS SiliconFlow',
  '自定义TTS': 'TTS tùy chỉnh', '机智云TTS': 'TTS Gizwits',
  'Linkerai语音合成': 'Tổng hợp giọng nói Linkerai',
  'Index-TTS-vLLM流式语音合成': 'Tổng hợp giọng nói liên tục Index-TTS-vLLM',
  'Minimax流式语音合成': 'Tổng hợp giọng nói liên tục Minimax',
  '讯飞流式语音识别': 'Nhận dạng giọng nói liên tục iFlytek',
  '讯飞流式语音合成': 'Tổng hợp giọng nói liên tục iFlytek',
  '豆包语音合成模型2.0': 'Mô hình tổng hợp giọng nói Doubao 2.0',
  '阿里云TTS': 'TTS Alibaba Cloud', '阿里云语音识别': 'Nhận dạng giọng nói Alibaba Cloud',
  '阿里云语音识别(流式)': 'Nhận dạng giọng nói liên tục Alibaba Cloud',
  '阿里云语音合成(流式)': 'Tổng hợp giọng nói liên tục Alibaba Cloud',
  '阿里百炼Paraformer实时语音识别': 'Nhận dạng giọng nói thời gian thực Alibaba Bailian Paraformer',
  '阿里百炼流式语音合成': 'Tổng hợp giọng nói liên tục Alibaba Bailian',
  '阿里百炼接口': 'API Alibaba Bailian', 'OpenAI接口': 'API OpenAI', 'ChatGLM接口': 'API ChatGLM',
  'Coze接口': 'API Coze', 'Dify接口': 'API Dify', 'FastGPT接口': 'API FastGPT',
  'Gemini接口': 'API Gemini', 'Ollama接口': 'API Ollama', 'Xinference接口': 'API Xinference',
  'API地址': 'Địa chỉ API', 'API服务地址': 'Địa chỉ dịch vụ API', 'API密钥': 'Khóa API',
  '基础URL': 'URL cơ sở', 'OpenAI基础URL': 'URL cơ sở OpenAI',
  'Embedding OpenAI基础URL': 'URL cơ sở OpenAI cho embedding',
  'Embedding API密钥': 'Khóa API embedding', 'Embedding提供商': 'Nhà cung cấp embedding',
  'Embedding模型': 'Mô hình embedding', 'Embedding维度': 'Số chiều embedding',
  'LLM API密钥': 'Khóa API LLM', 'LLM提供商': 'Nhà cung cấp LLM', 'LLM模型': 'Mô hình LLM',
  'HTTP代理': 'Proxy HTTP', 'HTTPS代理': 'Proxy HTTPS', 'WebSocket地址': 'Địa chỉ WebSocket',
  'top_k值': 'Giá trị top_k', 'top_p值': 'Giá trị top_p',
  '个人访问令牌': 'Token truy cập cá nhân', '临时Token': 'Token tạm thời',
  '保存路径': 'Đường dẫn lưu', '保留书面语': 'Giữ văn phong viết',
  '函数列表': 'Danh sách hàm', '切分标点': 'Dấu câu phân đoạn', '动态修正': 'Hiệu chỉnh động',
  '区域': 'Khu vực', '协议类型': 'Loại giao thức', '参考ID': 'ID tham chiếu',
  '参考文本': 'Văn bản tham chiếu', '参考音频': 'Âm thanh tham chiếu',
  '参考音频路径': 'Đường dẫn âm thanh tham chiếu', '发音字典': 'Từ điển phát âm',
  '变量': 'Biến', '口语化等级': 'Mức độ khẩu ngữ', '向量存储配置(JSON)': 'Cấu hình lưu vector (JSON)',
  '启用用户画像': 'Bật hồ sơ người dùng', '响应格式': 'Định dạng phản hồi', '块长度': 'Độ dài khối',
  '对话模式': 'Chế độ hội thoại', '应用AppID': 'AppID ứng dụng', '应用AppKey': 'AppKey ứng dụng',
  '应用ID': 'ID ứng dụng', '应用密钥': 'Khóa ứng dụng', '引用的LLM模型': 'Mô hình LLM tham chiếu',
  '情感': 'Cảm xúc', '情感强度(1-5)': 'Cường độ cảm xúc (1–5)', '情感类型': 'Loại cảm xúc',
  '批处理大小': 'Kích thước lô', '批处理阈值': 'Ngưỡng xử lý theo lô',
  '指定语言编码': 'Mã ngôn ngữ', '授权': 'Ủy quyền', '提示文本': 'Văn bản gợi ý',
  '提示语言': 'Ngôn ngữ gợi ý', '文本分割方法': 'Phương pháp phân đoạn văn bản',
  '文本语言': 'Ngôn ngữ văn bản', '断句检测时间': 'Thời gian phát hiện kết thúc câu', '方言': 'Phương ngữ',
  '是否不使用本地prompt': 'Bỏ qua prompt cục bộ', '是否使用SR': 'Sử dụng SR', '是否使用SSL': 'Sử dụng SSL',
  '是否使用内存缓存': 'Sử dụng bộ nhớ đệm RAM', '是否分桶': 'Phân nhóm bucket',
  '是否口语化': 'Dùng văn phong khẩu ngữ', '是否并行推理': 'Suy luận song song',
  '是否开启多语种识别模式': 'Bật nhận dạng đa ngôn ngữ', '是否开启链接复用': 'Tái sử dụng kết nối',
  '是否标准化': 'Chuẩn hóa', '是否流式': 'Truyền dữ liệu liên tục',
  '是否流式模式': 'Chế độ truyền dữ liệu liên tục', '是否返回片段': 'Trả về các đoạn',
  '替换词文件名称': 'Tên tệp từ thay thế', '最大令牌数': 'Số token tối đa',
  '最大新令牌数': 'Số token mới tối đa', '最小静音时长': 'Thời gian im lặng tối thiểu',
  '服务地址': 'Địa chỉ dịch vụ', '服务端拆句': 'Phân đoạn câu trên server', '服务类型': 'Loại dịch vụ',
  '机器人ID': 'ID bot', '格式': 'Định dạng', '检测阈值': 'Ngưỡng phát hiện',
  '模型': 'Mô hình', '模型名称': 'Tên mô hình', '模型目录': 'Thư mục mô hình', '模型路径': 'Đường dẫn mô hình',
  '混音控制配置': 'Cấu hình trộn âm', '温度': 'Nhiệt độ', '热词文件名称': 'Tên tệp từ khóa ưu tiên',
  '用户ID': 'ID người dùng', '目标语言': 'Ngôn ngữ đích', '种子': 'Seed', '端口号': 'Cổng',
  '组ID': 'ID nhóm', '记忆ID': 'ID bộ nhớ', '访问令牌': 'Token truy cập',
  '访问密钥ID': 'ID khóa truy cập', '访问密钥密码': 'Mật khẩu khóa truy cập',
  '识别语言': 'Ngôn ngữ nhận dạng', '识别领域': 'Lĩnh vực nhận dạng', '语言参数': 'Tham số ngôn ngữ',
  '语速': 'Tốc độ nói', '语速(-100~100)': 'Tốc độ nói (-100–100)', '语速(-50~100)': 'Tốc độ nói (-50–100)',
  '请求参数': 'Tham số yêu cầu', '请求头': 'Header yêu cầu', '请求方式': 'Phương thức yêu cầu',
  '资源ID': 'ID tài nguyên', '辅助参考音频路径': 'Đường dẫn âm thanh tham chiếu bổ sung',
  '输入参考': 'Tham chiếu đầu vào', '输出目录': 'Thư mục đầu ra', '通道数': 'Số kênh',
  '速度': 'Tốc độ', '速度因子': 'Hệ số tốc độ', '采样步数': 'Số bước lấy mẫu', '采样率': 'Tần số lấy mẫu',
  '重复惩罚': 'Hệ số phạt lặp lại', '集群': 'Cụm', '静音判定时长(ms)': 'Thời gian xác định im lặng (ms)',
  '音色': 'Giọng đọc', '音色ID': 'ID giọng đọc', '音色权重': 'Trọng số giọng đọc', '音色设置': 'Cài đặt giọng đọc',
  '音调': 'Cao độ', '音调(-100~100)': 'Cao độ (-100–100)', '音调因子': 'Hệ số cao độ',
  '音量': 'Âm lượng', '音量(-50~100)': 'Âm lượng (-50–100)', '音量(0~100)': 'Âm lượng (0–100)',
  '音量变化': 'Thay đổi âm lượng', '音量增益': 'Độ khuếch đại âm lượng',
  '音频格式': 'Định dạng âm thanh', '音频设置': 'Cài đặt âm thanh', '音频输出配置': 'Cấu hình đầu ra âm thanh',
  '音高': 'Cao độ', '音高(-12~12)': 'Cao độ (-12–12)', '频率惩罚': 'Hệ số phạt tần suất',
  '高级文本处理配置': 'Cấu hình xử lý văn bản nâng cao', '默认音色': 'Giọng đọc mặc định',
  '参数管理': 'Quản lý tham số', '知识库管理': 'Quản lý kho tri thức', '服务端管理': 'Quản lý server',
  'OTA管理': 'Quản lý OTA', '音色资源开通': 'Kích hoạt tài nguyên giọng đọc',
  '音色克隆管理': 'Quản lý nhân bản giọng nói', '功能配置': 'Cấu hình chức năng',
  '替换词管理': 'Quản lý từ thay thế', '通讯录管理': 'Quản lý danh bạ',
  '公钥不能为null或undefined': 'Khóa công khai không được là null hoặc undefined',
  '明文不能为空': 'Văn bản cần mã hóa không được để trống', '暂无': 'Chưa có',
  '系统功能菜单配置': 'Cấu hình menu chức năng hệ thống',
  '刷新': 'Tải lại', '发现新版本，点击刷新应用': 'Có phiên bản mới. Nhấn để tải lại ứng dụng',
  '似乎无法连接服务器': 'Không thể kết nối tới server', '正在连接服务器(': 'Đang kết nối tới server (',
  '网络请求出现了错误【': 'Yêu cầu mạng gặp lỗi [',
};

const catalog = Object.fromEntries(Object.keys(zhCN).map(key => [zhCN[key], vi[key]]));
const dictionary = { ...catalog, ...labels };

const actions = {
  '获取': 'Không thể lấy', '新增': 'Không thể thêm', '创建': 'Không thể tạo',
  '更新': 'Không thể cập nhật', '删除': 'Không thể xóa', '批量删除': 'Không thể xóa hàng loạt',
  '上传': 'Không thể tải lên', '解析': 'Không thể phân tích', '设置默认': 'Không thể đặt mặc định cho',
};
const resources = {
  '供应器列表': 'danh sách nhà cung cấp', '模型': 'mô hình', '模型配置': 'cấu hình mô hình',
  '模型状态': 'trạng thái mô hình', '模型供应器': 'nhà cung cấp mô hình',
  '插件列表': 'danh sách plugin', 'RAG模型列表': 'danh sách mô hình RAG', 'OTA状态': 'trạng thái OTA',
  '知识库列表': 'danh sách kho tri thức', '知识库': 'kho tri thức',
  '文档列表': 'danh sách tài liệu', '文档': 'tài liệu', '切片列表': 'danh sách đoạn văn bản',
  '字典类型列表': 'danh sách loại từ điển', '字典类型详情': 'chi tiết loại từ điển',
  '字典类型': 'loại từ điển', '字典数据列表': 'danh sách dữ liệu từ điển',
  '字典数据详情': 'chi tiết dữ liệu từ điển', '字典数据': 'dữ liệu từ điển',
};
for (const [action, translatedAction] of Object.entries(actions)) {
  for (const [resource, translatedResource] of Object.entries(resources)) {
    dictionary[`${action}${resource}失败`] = `${translatedAction} ${translatedResource}`;
  }
}
dictionary['召回测试失败'] = 'Kiểm tra truy xuất thất bại';

export const systemTextTranslations = dictionary;

export function localizeSystemText(value, locale = 'vi') {
  if (locale !== 'vi' || typeof value !== 'string') return value;
  return dictionary[value] || value;
}
