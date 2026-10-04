package xiaozhi.modules.agent.service.biz;

import xiaozhi.modules.agent.dto.AgentChatHistoryReportDTO;

/**
 * Lớp logic kinh doanh lịch sử trò chuyện của tổng đài viên
 *
 * @author Goody
 * @version 1.0, 2025/4/30
 * @since 1.0.0
 */
public interface AgentChatHistoryBizService {

    /**
     * Phương thức báo cáo trò chuyện
     *
     * @param agentChatHistoryReportDTO đối tượng đầu vào chứa thông tin cần thiết để báo cáo trò chuyện
     *                                  Ví dụ: địa chỉ MAC của thiết bị, loại tệp, nội dung, v.v.
     * @return Kết quả upload, true nghĩa là thành công, false nghĩa là thất bại
     */
    Boolean report(AgentChatHistoryReportDTO agentChatHistoryReportDTO);
}
