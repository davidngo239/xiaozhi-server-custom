package xiaozhi.modules.agent.service;

/**
 * Giao diện dịch vụ tóm tắt bản ghi cuộc trò chuyện của đại lý
 */
public interface AgentChatSummaryService {

    /**
     * Tạo bản tóm tắt bản ghi trò chuyện dựa trên ID phiên và lưu vào bộ nhớ tổng đài viên
     * 
     * @param sessionId ID phiên
     * @return lưu kết quả
     */
    boolean generateAndSaveChatSummary(String sessionId);

    /**
     * Tạo tiêu đề trò chuyện dựa trên ID phiên và lưu
     *
     * @param sessionId ID phiên
     * @return xem có thành công không
     */
    boolean generateAndSaveChatTitle(String sessionId);
}