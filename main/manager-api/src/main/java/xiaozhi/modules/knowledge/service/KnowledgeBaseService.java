package xiaozhi.modules.knowledge.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.knowledge.dto.KnowledgeBaseDTO;
import xiaozhi.modules.knowledge.entity.KnowledgeBaseEntity;
import xiaozhi.modules.model.entity.ModelConfigEntity;

/**
 * Giao diện dịch vụ cơ sở tri thức
 */
public interface KnowledgeBaseService extends BaseService<KnowledgeBaseEntity> {

    /**
     * Truy vấn danh sách cơ sở kiến thức theo trang
     * 
     * @param KnowledgeBaseDTO điều kiện truy vấn
     * @param số trang
     * Số giới hạn @param trên mỗi trang
     * @return dữ liệu được phân trang
     */
    PageData<KnowledgeBaseDTO> getPageList(KnowledgeBaseDTO knowledgeBaseDTO, Integer page, Integer limit);

    /**
     * Nhận thông tin chi tiết về cơ sở kiến thức dựa trên ID
     * 
     * @param id ID cơ sở kiến thức
     * @return chi tiết cơ sở kiến thức
     */
    KnowledgeBaseDTO getById(String id);

    /**
     * Thêm nền tảng kiến thức mới
     * 
     * @param KnowledgeBaseDTO thông tin cơ sở kiến thức
     * @return Cơ sở kiến thức mới
     */
    KnowledgeBaseDTO save(KnowledgeBaseDTO knowledgeBaseDTO);

    /**
     * Cập nhật cơ sở kiến thức
     * 
     * @param KnowledgeBaseDTO thông tin cơ sở kiến thức
     * @return cập nhật cơ sở kiến thức
     */
    KnowledgeBaseDTO update(KnowledgeBaseDTO knowledgeBaseDTO);

    /**
     * Truy vấn cơ sở tri thức dựa trên ID cơ sở tri thức
     * 
     * @paramdatadataID cơ sở kiến thức ID
     * @return chi tiết cơ sở kiến thức
     */
    KnowledgeBaseDTO getByDatasetId(String datasetId);

    /**
     * Truy vấn cơ sở tri thức dựa trên bộ ID cơ sở tri thức
     *
     * @param tập dữ liệuIdList Bộ sưu tập ID cơ sở tri thức
     * @return chi tiết cơ sở kiến thức
     */
    List<KnowledgeBaseDTO> getByDatasetIdList(List<String> datasetIdList);

    /**
     * Xóa cơ sở tri thức dựa trên ID của nó
     * 
     * @paramdatadataID cơ sở kiến thức ID
     */
    void deleteByDatasetId(String datasetId);

    /**
     * Nhận thông tin cấu hình RAG
     * 
     * @param ragModelId ID cấu hình mô hình RAG
     * @return thông tin cấu hình RAG
     */
    Map<String, Object> getRAGConfig(String ragModelId);

    /**
     * Nhận cấu hình RAG tương ứng dựa trên ID cơ sở kiến thức
     * 
     * @paramdatadataID cơ sở kiến thức ID
     * @return cấu hình RAG
     */
    Map<String, Object> getRAGConfigByDatasetId(String datasetId);

    /**
     * Nhận danh sách mô hình RAG
     * 
     * @return danh sách mô hình RAG
     */
    List<ModelConfigEntity> getRAGModels();

    /**
     * Cập nhật số liệu thống kê cơ sở kiến thức (được sử dụng bởi lệnh gọi lại dịch vụ tệp)
     * 
     * @paramdatadataID cơ sở kiến thức ID
     * @param docDelta tăng số tài liệu
     * @param chunkDelta tăng số đoạn
     * @param tokenDelta Tăng số lượng mã thông báo
     */
    void updateStatistics(String datasetId, Integer docDelta, Long chunkDelta, Long tokenDelta);
}