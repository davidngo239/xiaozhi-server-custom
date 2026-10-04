package xiaozhi.modules.knowledge.service;

import java.util.List;
import java.util.Map;

import org.springframework.web.multipart.MultipartFile;

import xiaozhi.common.page.PageData;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;
import xiaozhi.modules.knowledge.dto.document.ChunkDTO;
import xiaozhi.modules.knowledge.dto.document.RetrievalDTO;
import xiaozhi.modules.knowledge.dto.document.DocumentDTO;

/**
 * Giao diện dịch vụ tài liệu cơ sở kiến thức
 */
public interface KnowledgeFilesService {

        /**
         * Truy vấn danh sách tài liệu theo trang
         * 
         * @param KnowledgeFilesDTO điều kiện truy vấn
         * @param số trang
         * Số giới hạn @param trên mỗi trang
         * @return dữ liệu được phân trang
         */
        PageData<KnowledgeFilesDTO> getPageList(KnowledgeFilesDTO knowledgeFilesDTO, Integer page, Integer limit);

        /**
         * Nhận chi tiết tài liệu dựa trên ID tài liệu và ID cơ sở kiến thức
         * 
         * @param documentId ID tài liệu
         * @paramdatadataID cơ sở kiến thức ID
         * @return chi tiết tài liệu (được gõ mạnh InfoVO)
         */
        DocumentDTO.InfoVO getByDocumentId(String documentId, String datasetId);

        /**
         * Tải tài liệu lên cơ sở tri thức
         * 
         * @paramdatadataID cơ sở kiến thức ID
         * @param tập tin đã tải lên tập tin
         * @param tên tên tài liệu
         * Các trường siêu dữ liệu @param metaFields
         * @param chunkMethod Phương thức Chunking
         * @param ParserConfig Cấu hình trình phân tích cú pháp
         * @return thông tin tài liệu đã tải lên
         */
        KnowledgeFilesDTO uploadDocument(String datasetId, MultipartFile file, String name,
                        Map<String, Object> metaFields, String chunkMethod,
                        Map<String, Object> parserConfig);

        /**
         * Xóa tài liệu theo đợt
         * 
         * @paramdatadataID cơ sở kiến thức ID
         * @param req xóa các tham số yêu cầu (bao gồm danh sách ID tài liệu)
         */
        void deleteDocuments(String datasetId, DocumentDTO.BatchIdReq req);

        /**
         * Nhận thông tin cấu hình RAG
         * 
         * @param ragModelId ID cấu hình mô hình RAG
         * @return thông tin cấu hình RAG
         */
        Map<String, Object> getRAGConfig(String ragModelId);

        /**
         * Phân tích tài liệu (cắt thành từng đoạn)
         * 
         * @paramdatadataID cơ sở kiến thức ID
         * @param documentIds danh sách ID tài liệu
         * @return kết quả phân tích cú pháp
         */
        boolean parseDocuments(String datasetId, List<String> documentIds);

        /**
         * Liệt kê các lát của tài liệu được chỉ định
         * 
         * @paramdatadataID cơ sở kiến thức ID
         * @param documentId ID tài liệu
         * @param req tham số yêu cầu danh sách lát cắt
         * @return thông tin danh sách lát
         */
        ChunkDTO.ListVO listChunks(String datasetId, String documentId, ChunkDTO.ListReq req);

        /**
         * kiểm tra thu hồi
         * 
         * @param req truy xuất các tham số yêu cầu kiểm tra
         * @return thu hồi kết quả kiểm tra
         */
        RetrievalDTO.ResultVO retrievalTest(RetrievalDTO.TestReq req);

        /**
         * Lưu bản ghi bóng tài liệu
         */
        boolean saveDocumentShadow(String datasetId, KnowledgeFilesDTO result, String originalName, String chunkMethod,
                        Map<String, Object> parserConfig);

        /**
         * Xóa hàng loạt bản ghi bóng tài liệu và đồng bộ hóa số liệu thống kê
         * 
         * @param documentIds danh sách ID tài liệu
         * @param tập dữ liệuId ID tập dữ liệu
         * @param chunkDelta Tổng số khối được khấu trừ
         * @param tokenDelta Tổng số token được khấu trừ
         */
        void deleteDocumentShadows(List<String> documentIds, String datasetId, Long chunkDelta, Long tokenDelta);

        /**
         * Làm sạch tất cả các tài liệu liên quan dựa trên ID tập dữ liệu (chỉ dành cho xóa tầng)
         * 
         * @param tập dữ liệuId ID tập dữ liệu
         */
        void deleteDocumentsByDatasetId(String datasetId);

        /**
         * Đồng bộ hóa tất cả tài liệu ở trạng thái CHẠY (đối với các cuộc gọi tác vụ đã lên lịch)
         */
        void syncRunningDocuments();

        /**
         * Đồng bộ hóa tất cả tài liệu từ RAGFlow sang bảng bóng cục bộ
         * Kéo tất cả tài liệu từ đầu xa, so sánh chúng với bảng bóng cục bộ và chèn các bản ghi bị thiếu
         *
         * @param tập dữ liệuId ID tập dữ liệu
         * @return Số lượng tài liệu mới được đồng bộ
         */
        int syncDocumentsFromRAG(String datasetId);
}