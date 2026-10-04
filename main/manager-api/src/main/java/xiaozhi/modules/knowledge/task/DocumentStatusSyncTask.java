package xiaozhi.modules.knowledge.task;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.modules.knowledge.service.KnowledgeFilesService;

/**
 * Nhiệm vụ theo lịch trình đồng bộ hóa trạng thái tài liệu cơ sở kiến thức
 * 
 * chức năng:
 * 1. Tự động quét tài liệu ở trạng thái “ĐANG CHẠY” (parsing)
 * 2. Gọi giao diện RAGFlow để nhận trạng thái mới nhất
 * 3. Khi chuyển trạng thái (CHẠY -> THÀNH CÔNG/THẤT BẠI), cơ sở dữ liệu được cập nhật đồng bộ
 * 4. [Key] Khi phân tích thành công, bù và cập nhật thông tin thống kê của cơ sở tri thức (TokenCount)
 */
@Component
@AllArgsConstructor
@Slf4j
public class DocumentStatusSyncTask {

    private final KnowledgeFilesService knowledgeFilesService;

    /**
     * Thực hiện đồng bộ hóa cứ sau 30 giây
     * Sử dụng cố địnhDelay để đảm bảo rằng lần thực thi tiếp theo được bắt đầu 30 giây sau lần thực hiện cuối cùng để ngăn chặn tình trạng tồn đọng
     */
    @Scheduled(fixedDelay = 30000)
    public void syncRunningDocuments() {
        try {
            // log.debug("Bắt đầu thực thi tác vụ đồng bộ hóa trạng thái tài liệu...");
            knowledgeFilesService.syncRunningDocuments();
        } catch (Exception e) {
            log.error("文档状态同步任务异常", e);
        }
    }
}
