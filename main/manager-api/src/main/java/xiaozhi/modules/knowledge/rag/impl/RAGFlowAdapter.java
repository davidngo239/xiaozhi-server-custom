package xiaozhi.modules.knowledge.rag.impl;

import java.io.IOException;
import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

import org.apache.commons.lang3.StringUtils;
import org.springframework.core.io.AbstractResource;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.multipart.MultipartFile;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;
import xiaozhi.modules.knowledge.dto.dataset.DatasetDTO;
import xiaozhi.modules.knowledge.dto.document.ChunkDTO;
import xiaozhi.modules.knowledge.dto.document.RetrievalDTO;
import xiaozhi.modules.knowledge.dto.document.DocumentDTO;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapter;
import xiaozhi.modules.knowledge.rag.RAGFlowClient;

/**
 * Triển khai bộ điều hợp cơ sở tri thức RAGFlow
 * <p>
 * Lưu ý tái cấu trúc:
 * Lớp này đã được nâng cấp để sử dụng {@link RAGFlowClient} nhằm xử lý thống nhất các giao tiếp HTTP.
 * Đã giải quyết vấn đề thiếu Thời gian chờ và Xử lý lỗi rải rác trong mã cũ.
 * </p>
 */
@Slf4j
public class RAGFlowAdapter extends KnowledgeBaseAdapter {

    private static final String ADAPTER_TYPE = "ragflow";

    private Map<String, Object> config;
    private ObjectMapper objectMapper;
    // Phiên bản máy khách, được tạo trong quá trình khởi tạo
    private RAGFlowClient client;

    public RAGFlowAdapter() {
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public String getAdapterType() {
        return ADAPTER_TYPE;
    }

    @Override
    public void initialize(Map<String, Object> config) {
        this.config = config;
        validateConfig(config);

        String baseUrl = getConfigValue(config, "base_url", "baseUrl");
        String apiKey = getConfigValue(config, "api_key", "apiKey");

        // Khởi tạo Client, thời gian chờ mặc định là 30s, có thể kéo dài thông qua config
        int timeout = 30;
        Object timeoutObj = getConfigValue(config, "timeout", "timeout");
        if (timeoutObj != null) {
            try {
                timeout = Integer.parseInt(timeoutObj.toString());
            } catch (Exception e) {
                log.warn("解析超时配置失败，使用默认值 30s");
            }
        }
        this.client = new RAGFlowClient(baseUrl, apiKey, timeout);
        log.info("RAGFlow适配器初始化完成，Client已就绪");
    }

    @Override
    public boolean validateConfig(Map<String, Object> config) {
        if (config == null) {
            throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND);
        }

        String baseUrl = getConfigValue(config, "base_url", "baseUrl");
        String apiKey = getConfigValue(config, "api_key", "apiKey");

        if (StringUtils.isBlank(baseUrl)) {
            throw new RenException(ErrorCode.RAG_API_ERROR_URL_NULL);
        }

        if (StringUtils.isBlank(apiKey)) {
            throw new RenException(ErrorCode.RAG_API_ERROR_API_KEY_NULL);
        }

        if (apiKey.contains("你")) {
            throw new RenException(ErrorCode.RAG_API_ERROR_API_KEY_INVALID);
        }

        if (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://")) {
            throw new RenException(ErrorCode.RAG_API_ERROR_URL_INVALID);
        }

        return true;
    }

    /**
     * Phương thức phụ trợ: hỗ trợ nhiều cấu hình thu thập tên khóa (tương thích với CamelCase và Snake_case)
     */
    private String getConfigValue(Map<String, Object> config, String snakeKey, String camelKey) {
        if (config.containsKey(snakeKey)) {
            return (String) config.get(snakeKey);
        }
        if (config.containsKey(camelKey)) {
            return (String) config.get(camelKey);
        }
        return null;
    }

    /**
     * Phương thức trợ giúp: Đảm bảo Máy khách được khởi tạo
     */
    private RAGFlowClient getClient() {
        if (this.client == null) {
            // Cố gắng khởi động lại
            if (this.config != null) {
                initialize(this.config);
            } else {
                throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND, "适配器未初始化"); // nên ném RuntimeException
            }
        }
        return this.client;
    }

    private RenException convertToRenException(Exception e) {
        if (e instanceof RenException) {
            return (RenException) e;
        }
        return new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
    }

    @Override
    public PageData<KnowledgeFilesDTO> getDocumentList(String datasetId, DocumentDTO.ListReq req) {
        try {
            log.info("=== [RAGFlow] 获取文档列表: datasetId={} ===", datasetId);

            // Sử dụng Jackson để chuyển đổi DTO thành Map làm tham số truy vấn
            Map<String, Object> params = objectMapper.convertValue(req, new TypeReference<Map<String, Object>>() {
            });

            Map<String, Object> response = getClient().get("/api/v1/datasets/" + datasetId + "/documents", params);

            Object dataObj = response.get("data");
            return parseDocumentListResponse(dataObj, req.getPage() != null ? req.getPage() : 1,
                    req.getPageSize() != null ? req.getPageSize() : 10);

        } catch (Exception e) {
            log.error("获取文档列表失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public DocumentDTO.InfoVO getDocumentById(String datasetId, String documentId) {
        try {
            log.info("=== [RAGFlow] 获取文档详情: datasetId={}, documentId={} ===", datasetId, documentId);
            DocumentDTO.ListReq req = DocumentDTO.ListReq.builder()
                    .id(documentId)
                    .page(1)
                    .pageSize(1)
                    .build();

            Map<String, Object> params = objectMapper.convertValue(req, new TypeReference<Map<String, Object>>() {
            });
            Map<String, Object> response = getClient().get("/api/v1/datasets/" + datasetId + "/documents", params);

            Object dataObj = response.get("data");
            if (dataObj instanceof Map<?, ?> dataMap) {
                List<?> documents = (List<?>) dataMap.get("docs");
                if (documents != null && !documents.isEmpty()) {
                    return objectMapper.convertValue(documents.get(0), DocumentDTO.InfoVO.class);
                }
            }
            return null;
        } catch (Exception e) {
            log.error("获取文档详情失败: documentId={}", documentId, e);
            throw convertToRenException(e);
        }
    }

    @Override
    public KnowledgeFilesDTO uploadDocument(DocumentDTO.UploadReq req) {
        String datasetId = req.getDatasetId();
        MultipartFile file = req.getFile();
        try {
            log.info("=== [RAGFlow] 上传文档: datasetId={} ===", datasetId);

            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("file", new MultipartFileResource(file));

            if (StringUtils.isNotBlank(req.getName())) {
                body.add("name", req.getName());
            }
            if (req.getMetaFields() != null && !req.getMetaFields().isEmpty()) {
                body.add("meta", objectMapper.writeValueAsString(req.getMetaFields()));
            }
            if (req.getChunkMethod() != null) {
                // Chuyển đổi giá trị liệt kê thành chuỗi mà RAGFlow mong đợi (chẳng hạn như NAIVE -> ngây thơ)
                body.add("chunk_method", req.getChunkMethod().name().toLowerCase());
            }
            if (req.getParserConfig() != null) {
                body.add("parser_config", objectMapper.writeValueAsString(req.getParserConfig()));
            }
            if (StringUtils.isNotBlank(req.getParentPath())) {
                body.add("parent_path", req.getParentPath());
            }

            Map<String, Object> response = getClient().postMultipart("/api/v1/datasets/" + datasetId + "/documents",
                    body);

            Object dataObj = response.get("data");
            return parseUploadResponse(dataObj, datasetId, file);

        } catch (Exception e) {
            log.error("文档上传失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public PageData<KnowledgeFilesDTO> getDocumentListByStatus(String datasetId, Integer status, Integer page,
            Integer limit) {
        List<DocumentDTO.InfoVO.RunStatus> runStatusList = null;
        if (status != null) {
            runStatusList = new ArrayList<>();
            switch (status) {
                case 0:
                    runStatusList.add(DocumentDTO.InfoVO.RunStatus.UNSTART);
                    break;
                case 1:
                    runStatusList.add(DocumentDTO.InfoVO.RunStatus.RUNNING);
                    break;
                case 2:
                    runStatusList.add(DocumentDTO.InfoVO.RunStatus.CANCEL);
                    break;
                case 3:
                    runStatusList.add(DocumentDTO.InfoVO.RunStatus.DONE);
                    break;
                case 4:
                    runStatusList.add(DocumentDTO.InfoVO.RunStatus.FAIL);
                    break;
                default:
                    break;
            }
        }
        DocumentDTO.ListReq req = DocumentDTO.ListReq.builder()
                .run(runStatusList)
                .page(page)
                .pageSize(limit)
                .build();
        return getDocumentList(datasetId, req);
    }

    @Override
    public void deleteDocument(String datasetId, DocumentDTO.BatchIdReq req) {
        try {
            log.info("=== [RAGFlow] 批量删除文档: datasetId={}, count={} ===", datasetId,
                    req.getIds() != null ? req.getIds().size() : 0);
            getClient().delete("/api/v1/datasets/" + datasetId + "/documents", req);
        } catch (Exception e) {
            log.error("批量删除文档失败: datasetId={}", datasetId, e);
            throw convertToRenException(e);
        }
    }

    @Override
    public boolean parseDocuments(String datasetId, List<String> documentIds) {
        try {
            log.info("=== [RAGFlow] 解析文档 ===");
            Map<String, Object> body = new HashMap<>();
            body.put("document_ids", documentIds);

            getClient().post("/api/v1/datasets/" + datasetId + "/chunks", body);
            return true;
        } catch (Exception e) {
            log.error("解析文档失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public ChunkDTO.ListVO listChunks(String datasetId, String documentId, ChunkDTO.ListReq req) {
        try {
            // [Tái cấu trúc đèn lồng] Sử dụng objectMapper để chuyển đổi động các tham số truy vấn và loại bỏ mã hóa cứng
            Map<String, Object> params = objectMapper.convertValue(req, new TypeReference<Map<String, Object>>() {
            });

            Map<String, Object> response = getClient()
                    .get("/api/v1/datasets/" + datasetId + "/documents/" + documentId + "/chunks", params);

            Object dataObj = response.get("data");
            if (dataObj == null) {
                log.warn("[RAGFlow] listChunks 响应 data 为空, docId={}", documentId);
                return ChunkDTO.ListVO.builder()
                        .chunks(new ArrayList<>())
                        .total(0L)
                        .build();
            }

            ChunkDTO.ListVO result = objectMapper.convertValue(dataObj, ChunkDTO.ListVO.class);
            if (result.getTotal() == null) {
                result.setTotal(0L);
            }
            return result;
        } catch (Exception e) {
            log.error("获取切片失败: docId={}", documentId, e);
            throw convertToRenException(e);
        }
    }

    @Override
    public RetrievalDTO.ResultVO retrievalTest(RetrievalDTO.TestReq req) {
        try {
            // [Củng cố sản xuất] Căn chỉnh phòng thủ đối số: RAGFlow Python side nhạy cảm với 0 hoặc phân trang phủ định
            // Giải quyết ValueError('Tìm kiếm không hỗ trợ cắt âm.')
            if (req.getPage() != null && req.getPage() < 1) {
                req.setPage(1);
            }
            if (req.getPageSize() != null && req.getPageSize() < 1) {
                req.setPageSize(10); // 10 mục mặc định
            }
            if (req.getTopK() != null && req.getTopK() < 1) {
                req.setTopK(1024); // TopK mặc định nội bộ RAGFlow
            }
            // Chuẩn hóa ngưỡng tương tự (0,0 ~ 1,0)
            if (req.getSimilarityThreshold() != null) {
                if (req.getSimilarityThreshold() < 0f)
                    req.setSimilarityThreshold(0.2f);
                if (req.getSimilarityThreshold() > 1f)
                    req.setSimilarityThreshold(1.0f);
            }

            // [Tái tạo đèn lồng] Truyền trực tiếp và minh bạch DTO loại mạnh và getClient xử lý việc tuần tự hóa
            Map<String, Object> response = getClient().post("/api/v1/retrieval", req);

            Object dataObj = response.get("data");
            if (dataObj == null) {
                log.warn("[RAGFlow] retrievalTest 响应 data 为空");
                return RetrievalDTO.ResultVO.builder()
                        .chunks(new ArrayList<>())
                        .docAggs(new ArrayList<>())
                        .total(0L)
                        .build();
            }

            RetrievalDTO.ResultVO result = objectMapper.convertValue(dataObj, RetrievalDTO.ResultVO.class);
            if (result.getTotal() == null) {
                result.setTotal(0L);
            }
            return result;
        } catch (Exception e) {
            log.error("召回测试失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public boolean testConnection() {
        try {
            getClient().get("/api/v1/health", null);
            return true;
        } catch (Exception e) {
            log.error("连接测试失败: {}", e.getMessage());
            return false;
        }
    }

    @Override
    public Map<String, Object> getStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("adapterType", getAdapterType());
        status.put("configKeys", config != null ? config.keySet() : "未配置");
        status.put("connectionTest", testConnection());
        status.put("lastChecked", new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date()));
        return status;
    }

    @Override
    public Map<String, Object> getSupportedConfig() {
        Map<String, Object> supportedConfig = new HashMap<>();
        supportedConfig.put("base_url", "RAGFlow API基础URL");
        supportedConfig.put("api_key", "RAGFlow API密钥");
        supportedConfig.put("timeout", "请求超时时间（毫秒）");
        return supportedConfig;
    }

    @Override
    public Map<String, Object> getDefaultConfig() {
        Map<String, Object> defaultConfig = new HashMap<>();
        defaultConfig.put("timeout", 30000);
        return defaultConfig;
    }

    @Override
    public DatasetDTO.InfoVO createDataset(DatasetDTO.CreateReq req) {
        try {
            // [Sửa lỗi sản xuất] Tăng cường xử lý giá trị mặc định để ngăn API RAGFlow báo cáo lỗi do chuỗi trống hoặc trường bị thiếu (Mã 101)
            // Giải quyết "Trường: <avatar> - Thông báo: <Thiếu tiền tố MIME>" và các lỗi xác minh khác
            if (StringUtils.isBlank(req.getPermission())) {
                req.setPermission("me");
            }
            if (StringUtils.isBlank(req.getChunkMethod())) {
                req.setChunkMethod("naive");
            }

            // 🤖 Tự động hoàn thiện các mô hình nhúng: sử dụng tham số yêu cầu trước, sau đó sử dụng mô hình mặc định trong cấu hình
            if (StringUtils.isBlank(req.getEmbeddingModel())) {
                String defaultModel = (String) getConfigValue(config, "embedding_model", "embeddingModel");
                if (StringUtils.isNotBlank(defaultModel)) {
                    log.info("RAGFlow: 使用配置中的默认嵌入模型: {}", defaultModel);
                    req.setEmbeddingModel(defaultModel);
                }
                // Nếu không có giá trị mặc định trong cấu hình, hãy để trống và để máy chủ RAGFlow xử lý nó (hoặc đưa ra một ngoại lệ nghiệp vụ)
            }

            // 🖼️ Hình đại diện tự động hoàn thành: Nếu trống, hãy cung cấp pixel trong suốt 1x1 để ngăn RAGFlow không xác minh Tiền tố MIME
            if (StringUtils.isBlank(req.getAvatar())) {
                req.setAvatar(
                        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==");
            }

            // Truyền trực tiếp đối tượng yêu cầu được gõ mạnh cho Máy khách và Jackson sẽ xử lý ánh xạ JsonProperty
            Map<String, Object> response = getClient().post("/api/v1/datasets", req);

            // Lấy dữ liệu một cách an toàn và thực hiện ánh xạ đầy đủ thông qua DatasetDTO.InfoVO
            Object dataObj = response.get("data");
            if (dataObj != null) {
                return objectMapper.convertValue(dataObj, DatasetDTO.InfoVO.class);
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, "Invalid response from createDataset: missing data object");
        } catch (Exception e) {
            log.error("创建数据集失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public DatasetDTO.InfoVO updateDataset(String datasetId, DatasetDTO.UpdateReq req) {
        try {
            // Đường dẫn đề xuất cập nhật API RAGFlow có ID
            Map<String, Object> response = getClient().put("/api/v1/datasets/" + datasetId, req);

            Object dataObj = response.get("data");
            if (dataObj != null) {
                return objectMapper.convertValue(dataObj, DatasetDTO.InfoVO.class);
            }
            return null;
        } catch (Exception e) {
            log.error("更新数据集失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public DatasetDTO.BatchOperationVO deleteDataset(DatasetDTO.BatchIdReq req) {
        try {
            // Giao diện xóa hàng loạt RAGFlow sử dụng DELETE /api/v1/datasets
            Map<String, Object> response = getClient().delete("/api/v1/datasets", req);

            Object dataObj = response.get("data");
            if (dataObj != null) {
                return objectMapper.convertValue(dataObj, DatasetDTO.BatchOperationVO.class);
            }
            return null;
        } catch (Exception e) {
            log.error("批量删除数据集失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public Integer getDocumentCount(String datasetId) {
        DatasetDTO.InfoVO info = getDatasetInfo(datasetId);
        if (info != null && info.getDocumentCount() != null) {
            return info.getDocumentCount().intValue();
        }
        return 0;
    }

    @Override
    public DatasetDTO.InfoVO getDatasetInfo(String datasetId) {
        try {
            Map<String, Object> params = new HashMap<>();
            params.put("id", datasetId);
            params.put("page", 1);
            params.put("page_size", 1);

            Map<String, Object> response = getClient().get("/api/v1/datasets", params);
            Object dataObj = response.get("data");

            if (dataObj instanceof List) {
                List<?> list = (List<?>) dataObj;
                if (!list.isEmpty()) {
                    return objectMapper.convertValue(list.get(0), DatasetDTO.InfoVO.class);
                }
            }
            // Tập dữ liệu không tồn tại ở phía RAGFlow
            return null;
        } catch (Exception e) {
            log.warn("获取数据集信息失败: datasetId={}, error={}", datasetId, e.getMessage());
            throw convertToRenException(e);
        }
    }

    @Override
    public void postStream(String endpoint, Object body, Consumer<String> onData) {
        try {
            getClient().postStream(endpoint, body, onData);
        } catch (Exception e) {
            log.error("流式请求失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public Object postSearchBotAsk(Map<String, Object> config, Object body,
            Consumer<String> onData) {
        // SearchBot thực sự là một trình bao bọc xung quanh việc truy xuất Tập dữ liệu hay nó là một API không có giấy tờ?
        // Giả sử rằng RAGFlow không có giao diện /searchbots rõ ràng để SDK gọi mà là Truy xuất tập dữ liệu hoặc Trò chuyện.
        // Nhưng theo BotDTO thì đó là /api/v1/searchbots/ask (giả sử)
        // Cấu hình ở đây có thể bị ghi đè hoặc chúng tôi chỉ sử dụng ứng dụng khách hiện có của phiên bản bộ điều hợp.
        // Nhưng có lẽ Bot sử dụng Khóa API khác? Thông thường, phiên bản Adaptor được liên kết với một Khóa.
        // Nếu Bot sử dụng Khóa hệ thống, hãy sử dụng trực tiếp getClient().

        // Giả sử bây giờ điểm cuối /api/v1/searchbots/ask tồn tại (hoặc tương tự)
        // Nếu phát trực tuyến:
        try {
            getClient().postStream("/api/v1/searchbots/ask", body, onData);
            return null;
        } catch (Exception e) {
            log.error("SearchBot Ask 失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public void postAgentBotCompletion(Map<String, Object> config, String agentId, Object body,
            Consumer<String> onData) {
        // AgentBot tương ứng với /api/v1/agentbots/{id}/completions
        try {
            getClient().postStream("/api/v1/agentbots/" + agentId + "/completions", body, onData);
        } catch (Exception e) {
            log.error("AgentBot Completion 失败", e);
            throw convertToRenException(e);
        }
    }

    // Sử dụng lại các phương pháp phân tích cú pháp phụ trợ ban đầu để duy trì khả năng tương thích
    // [Sửa lỗi] Không còn nuốt các ngoại lệ khử lưu huỳnh để tránh bị lớp trên đánh giá sai rằng "tài liệu đã bị xóa"
    private PageData<KnowledgeFilesDTO> parseDocumentListResponse(Object dataObj, long curPage, long pageSize) {
        if (dataObj == null) {
            return new PageData<>(new ArrayList<>(), 0);
        }

        Map<?, ?> dataMap = Map.class.cast(dataObj);
        List<?> documents = List.class.cast(dataMap.get("docs"));
        if (documents == null || documents.isEmpty()) {
            // RAGFlow trả về rõ ràng một danh sách tài liệu trống, đây là một "chân không" hợp pháp
            return new PageData<>(new ArrayList<>(), 0);
        }

        List<KnowledgeFilesDTO> list = new ArrayList<>();
        for (Object docObj : documents) {
            try {
                // Dung sai lỗi chuyển đổi một tài liệu: việc không giải tuần tự hóa một tài liệu không ảnh hưởng đến các tài liệu khác
                DocumentDTO.InfoVO info = objectMapper.convertValue(docObj, DocumentDTO.InfoVO.class);
                list.add(mapToKnowledgeFilesDTO(info, null));
            } catch (Exception e) {
                log.warn("[RAGFlow] 单文档 DTO 转换失败，跳过该文档: {}", e.getMessage());
            }
        }

        long total = 0;
        if (dataMap.containsKey("total")) {
            total = ((Number) dataMap.get("total")).longValue();
        }

        return new PageData<>(list, total);
    }

    private KnowledgeFilesDTO parseUploadResponse(Object dataObj, String datasetId, MultipartFile file) {
        KnowledgeFilesDTO result = null;

        // Cố gắng trích xuất ID tài liệu (documentId) từ dữ liệu phản hồi
        if (dataObj != null) {
            try {
                DocumentDTO.InfoVO info = null;
                if (dataObj instanceof Map) {
                    info = objectMapper.convertValue(dataObj, DocumentDTO.InfoVO.class);
                } else if (dataObj instanceof List) {
                    List<?> list = (List<?>) dataObj;
                    if (!list.isEmpty()) {
                        info = objectMapper.convertValue(list.get(0), DocumentDTO.InfoVO.class);
                    }
                }

                if (info != null) {
                    result = mapToKnowledgeFilesDTO(info, datasetId);
                }
            } catch (Exception e) {
                log.warn("解析上传响应数据失败: {}", e.getMessage());
            }
        }

        if (result == null) {
            log.error("未能从RAGFlow响应中提取到documentId，响应内容: {}", dataObj);
            // Một DTO được thu nhỏ chứa thông tin cơ bản phải được trả về thay vì null để ngăn NPE ngược dòng.
            result = new KnowledgeFilesDTO();
            result.setDatasetId(datasetId);
            result.setName(file.getOriginalFilename());
            result.setFileSize(file.getSize());
            result.setStatus("1");
        }

        return result;
    }

    /**
     * Ánh xạ InfoVO được gõ mạnh của RAGFlow tới KnowledgeFilesDTO được sử dụng nội bộ
     * Đảm bảo rằng tất cả các trường có sẵn (tên, kích thước, trạng thái, cấu hình, v.v.) được đồng bộ hóa hoàn toàn
     */
    private KnowledgeFilesDTO mapToKnowledgeFilesDTO(DocumentDTO.InfoVO info, String datasetId) {
        KnowledgeFilesDTO dto = new KnowledgeFilesDTO();
        if (info == null)
            return dto;

        dto.setId(info.getId());
        dto.setDocumentId(info.getId());
        dto.setDatasetId(StringUtils.isNotBlank(info.getDatasetId()) ? info.getDatasetId() : datasetId);
        dto.setName(info.getName());
        dto.setFileSize(info.getSize());

        // lập bản đồ trạng thái
        if (info.getRun() != null) {
            dto.setRun(info.getRun().name());
        }

        if (StringUtils.isNotBlank(info.getStatus())) {
            dto.setStatus(info.getStatus());
        } else {
            dto.setStatus("1"); // Được bật theo mặc định
        }

        // Đồng bộ hóa thời gian
        if (info.getCreateTime() != null) {
            dto.setCreatedAt(new Date(info.getCreateTime()));
        }
        if (info.getUpdateTime() != null) {
            dto.setUpdatedAt(new Date(info.getUpdateTime()));
        }

        // Hoàn thành siêu dữ liệu cốt lõi (Số 1)
        dto.setProgress(info.getProgress());
        dto.setThumbnail(info.getThumbnail());
        dto.setProcessDuration(info.getProcessDuration());
        dto.setSourceType(info.getSourceType());
        dto.setChunkCount(info.getChunkCount() != null ? info.getChunkCount().intValue() : 0);
        dto.setTokenCount(info.getTokenCount());
        dto.setError(info.getProgressMsg()); // Ánh xạ mô tả tiến trình tới lời nhắc thông báo lỗi

        // Đồng bộ hóa trường mở rộng
        dto.setMetaFields(info.getMetaFields());
        if (info.getChunkMethod() != null) {
            dto.setChunkMethod(info.getChunkMethod().name().toLowerCase());
        }
        if (info.getParserConfig() != null) {
            dto.setParserConfig(objectMapper.convertValue(info.getParserConfig(),
                    new TypeReference<Map<String, Object>>() {
                    }));
        }

        return dto;
    }

    private static class MultipartFileResource extends AbstractResource {
        private final MultipartFile multipartFile;

        public MultipartFileResource(MultipartFile multipartFile) {
            this.multipartFile = multipartFile;
        }

        @Override
        public String getDescription() {
            return "MultipartFile resource [" + multipartFile.getOriginalFilename() + "]";
        }

        @Override
        public String getFilename() {
            return multipartFile.getOriginalFilename();
        }

        @Override
        public InputStream getInputStream() throws IOException {
            return multipartFile.getInputStream();
        }

        @Override
        public long contentLength() throws IOException {
            return multipartFile.getSize();
        }

        @Override
        public boolean exists() {
            return !multipartFile.isEmpty();
        }
    }
}
