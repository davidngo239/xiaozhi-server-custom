package xiaozhi.modules.knowledge.service.impl;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import xiaozhi.modules.knowledge.service.KnowledgeBaseService;
import xiaozhi.modules.knowledge.service.KnowledgeFilesService;
import xiaozhi.modules.knowledge.service.KnowledgeManagerService;

import java.util.List;

@Service
@Slf4j
@RequiredArgsConstructor
public class KnowledgeManagerServiceImpl implements KnowledgeManagerService {

    private final KnowledgeBaseService knowledgeBaseService;
    private final KnowledgeFilesService knowledgeFilesService;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteDatasetWithFiles(String datasetId) {
        log.info("=== 级联删除开始: datasetId={} ===", datasetId);

        // 1. Trước tiên, hãy gọi dịch vụ tệp để dọn sạch tất cả các bản ghi tài liệu trong tập dữ liệu (bao gồm cả phía RAGFlow)
        log.info("Step 1: 清理关联文档...");
        knowledgeFilesService.deleteDocumentsByDatasetId(datasetId);

        // 2. Gọi lại dịch vụ cơ sở tri thức để đăng xuất hoàn toàn bộ dữ liệu (bao gồm cả bên RAGFlow)
        log.info("Step 2: 删除数据集主体...");
        knowledgeBaseService.deleteByDatasetId(datasetId);

        log.info("=== 级联删除成功: datasetId={} ===", datasetId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void batchDeleteDatasetsWithFiles(List<String> datasetIds) {
        if (datasetIds == null || datasetIds.isEmpty())
            return;
        log.info("=== 批量级联删除开始: count={} ===", datasetIds.size());
        for (String id : datasetIds) {
            deleteDatasetWithFiles(id);
        }
    }
}
