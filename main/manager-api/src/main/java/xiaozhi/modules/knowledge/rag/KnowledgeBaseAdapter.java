package xiaozhi.modules.knowledge.rag;

import java.util.List;
import java.util.Map;

import xiaozhi.modules.knowledge.dto.dataset.DatasetDTO;

import xiaozhi.common.page.PageData;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;
import xiaozhi.modules.knowledge.dto.document.DocumentDTO;
import xiaozhi.modules.knowledge.dto.document.ChunkDTO;
import xiaozhi.modules.knowledge.dto.document.RetrievalDTO;
import java.util.function.Consumer;

/**
 * Lớp cơ sở trừu tượng của Bộ điều hợp API cơ sở kiến thức
 * Xác định giao diện vận hành cơ sở kiến thức chung và hỗ trợ nhiều triển khai API back-end
 */
public abstract class KnowledgeBaseAdapter {

        /**
         * Nhận mã định danh loại bộ điều hợp
         * 
         * @return loại bộ chuyển đổi (chẳng hạn như: ragflow, milvus,pinecone, v.v.)
         */
        public abstract String getAdapterType();

        /**
         * Khởi tạo cấu hình bộ chuyển đổi
         * 
         * Tham số cấu hình @param config
         */
        public abstract void initialize(Map<String, Object> config);

        /**
         * Xác minh rằng cấu hình hợp lệ
         * 
         * Tham số cấu hình @param config
         * @return kết quả xác minh
         */
        public abstract boolean validateConfig(Map<String, Object> config);

        /**
         * Truy vấn danh sách tài liệu theo trang
         * 
         * @paramdatadataID cơ sở kiến thức ID
         * Tham số truy vấn @param queryParams
         * @param số trang
         * Số giới hạn @param trên mỗi trang
         * @return dữ liệu được phân trang
         */
        public abstract PageData<KnowledgeFilesDTO> getDocumentList(String datasetId,
                        DocumentDTO.ListReq req);

        /**
         * Nhận chi tiết tài liệu dựa trên ID tài liệu
         * 
         * @paramdatadataID cơ sở kiến thức ID
         * @param documentId ID tài liệu
         * @return chi tiết tài liệu (được gõ mạnh InfoVO)
         */
        public abstract DocumentDTO.InfoVO getDocumentById(String datasetId, String documentId);

        /**
         * Tải tài liệu lên cơ sở tri thức
         * 
         * @param req tham số yêu cầu tải lên
         * @return thông tin tài liệu đã tải lên
         */
        public abstract KnowledgeFilesDTO uploadDocument(DocumentDTO.UploadReq req);

        /**
         * Truy vấn danh sách tài liệu bằng cách phân trang theo trạng thái
         * 
         * @paramdatadataID cơ sở kiến thức ID
         * Trạng thái phân tích tài liệu trạng thái @param
         * @param số trang
         * Số giới hạn @param trên mỗi trang
         * @return dữ liệu được phân trang
         */
        public abstract PageData<KnowledgeFilesDTO> getDocumentListByStatus(String datasetId,
                        Integer status,
                        Integer page,
                        Integer limit);

        /**
         * Xóa tài liệu (hỗ trợ xóa hàng loạt)
         * 
         * @paramdatadataID cơ sở kiến thức ID
         * Đối tượng yêu cầu @param req chứa danh sách ID tài liệu
         */
        public abstract void deleteDocument(String datasetId, DocumentDTO.BatchIdReq req);

        /**
         * Phân tích tài liệu (cắt thành từng đoạn)
         * 
         * @paramdatadataID cơ sở kiến thức ID
         * @param documentIds danh sách ID tài liệu
         * @return kết quả phân tích cú pháp
         */
        public abstract boolean parseDocuments(String datasetId, List<String> documentIds);

        /**
         * Liệt kê các lát của tài liệu được chỉ định
         * 
         * @paramdatadataID cơ sở kiến thức ID
         * @param documentId ID tài liệu
         * @param req liệt kê các tham số yêu cầu (phân trang, từ khóa, v.v.)
         * @return danh sách lát VO
         */
        public abstract ChunkDTO.ListVO listChunks(String datasetId,
                        String documentId,
                        ChunkDTO.ListReq req);

        /**
         * Kiểm tra thu hồi - truy xuất các phần có liên quan từ cơ sở kiến thức
         * 
         * @param req truy xuất các tham số yêu cầu kiểm tra
         * @return thu hồi kết quả kiểm tra
         */
        public abstract RetrievalDTO.ResultVO retrievalTest(
                        RetrievalDTO.TestReq req);

        /**
         * kết nối thử nghiệm
         * 
         * @return kết quả kiểm tra kết nối
         */
        public abstract boolean testConnection();

        /**
         * Nhận thông tin trạng thái bộ điều hợp
         * 
         * @return thông tin trạng thái
         */
        public abstract Map<String, Object> getStatus();

        /**
         * Nhận thông số cấu hình được hỗ trợ
         * 
         * @return mô tả tham số cấu hình
         */
        public abstract Map<String, Object> getSupportedConfig();

        /**
         * Nhận cấu hình mặc định
         * 
         * @return cấu hình mặc định
         */
        public abstract Map<String, Object> getDefaultConfig();

        /**
         * Tạo một tập dữ liệu
         * 
         * @param req tạo tham số
         * @return chi tiết tập dữ liệu
         */
        public abstract DatasetDTO.InfoVO createDataset(DatasetDTO.CreateReq req);

        /**
         * Cập nhật tập dữ liệu
         * 
         * @param tập dữ liệuId ID tập dữ liệu
         * @param req thông số cập nhật
         * @return chi tiết tập dữ liệu
         */
        public abstract DatasetDTO.InfoVO updateDataset(String datasetId, DatasetDTO.UpdateReq req);

        /**
         * Xóa tập dữ liệu
         * 
         * @param req xóa tham số yêu cầu (bao gồm danh sách ID)
         * @return kết quả hoạt động hàng loạt
         */
        public abstract DatasetDTO.BatchOperationVO deleteDataset(DatasetDTO.BatchIdReq req);

        /**
         * Lấy số lượng tài liệu trong một tập dữ liệu
         *
         * @param tập dữ liệuId ID tập dữ liệu
         * @return số lượng tài liệu
         */
        public abstract Integer getDocumentCount(String datasetId);

        /**
         * Nhận thông tin đầy đủ về tập dữ liệu (tên, phần giới thiệu, số lượng tài liệu, v.v.)
         * Được sử dụng để phát hiện xem đầu RAGFlow có bị xóa hay không và đồng bộ hóa các thay đổi tên/hồ sơ
         *
         * @param tập dữ liệuId ID tập dữ liệu
         * @return Chi tiết tập dữ liệu, nếu đầu RAGFlow không tồn tại, trả về null
         */
        public abstract DatasetDTO.InfoVO getDatasetInfo(String datasetId);

        /**
         * Gửi yêu cầu phát trực tuyến (SSE)
         * 
         * Điểm cuối API điểm cuối @param
         * @param nội dung yêu cầu nội dung
         * @param onData gọi lại dữ liệu
         */
        public abstract void postStream(String endpoint, Object body, Consumer<String> onData);

        /**
         * SearchBot đã đặt câu hỏi
         *
         * @param config Cấu hình RAG
         * @param nội dung yêu cầu nội dung
         * @param onData gọi lại dữ liệu
         * @return đối tượng phản hồi
         */
        public abstract Object postSearchBotAsk(Map<String, Object> config, Object body,
                        Consumer<String> onData);

        /**
         * Đối thoại AgentBot
         *
         * @param config Cấu hình RAG
         * @param agentId Agent ID
         * @param nội dung yêu cầu nội dung
         * @param onData gọi lại dữ liệu
         */
        public abstract void postAgentBotCompletion(Map<String, Object> config, String agentId, Object body,
                        Consumer<String> onData);
}