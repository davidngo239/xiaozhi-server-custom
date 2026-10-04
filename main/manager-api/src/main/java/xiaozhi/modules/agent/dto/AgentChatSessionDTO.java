package xiaozhi.modules.agent.dto;

import java.time.LocalDateTime;

import lombok.Data;

/**
 * Danh sách phiên đại lý DTO
 */
@Data
public class AgentChatSessionDTO {
    /**
     * ID phiên
     */
    private String sessionId;

    /**
     * thời gian phiên
     */
    private LocalDateTime createdAt;

    /**
     * Số lượng cuộc trò chuyện
     */
    private Integer chatCount;

    /**
     * Tiêu đề phiên
     */
    private String title;
}