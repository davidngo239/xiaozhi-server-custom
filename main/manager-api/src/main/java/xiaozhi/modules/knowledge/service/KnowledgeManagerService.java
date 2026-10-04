package xiaozhi.modules.knowledge.service;

import java.util.List;

/**
 * Dịch vụ điều phối miền mô-đun cơ sở kiến thức
 * Được sử dụng để xử lý các quy trình kinh doanh phức tạp trên KnowledgeBase và KnowledgeFiles, đồng thời giải quyết hoàn toàn vấn đề phụ thuộc vòng tròn giữa các Dịch vụ.
 */
public interface KnowledgeManagerService {

    /**
     * Phân tầng xóa cơ sở kiến thức và tất cả các tài liệu cấp dưới của nó (bao gồm dữ liệu từ xa DB cục bộ và RAGFlow)
     * 
     * @paramdatadataID cơ sở kiến thức ID
     */
    void deleteDatasetWithFiles(String datasetId);

    /**
     * Xóa hàng loạt cơ sở kiến thức
     * 
     * @param tập dữ liệuIds Danh sách ID cơ sở kiến thức
     */
    void batchDeleteDatasetsWithFiles(List<String> datasetIds);
}
