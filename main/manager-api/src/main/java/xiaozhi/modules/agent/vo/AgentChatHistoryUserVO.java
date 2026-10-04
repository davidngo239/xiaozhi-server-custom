package xiaozhi.modules.agent.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * VO của dữ liệu trò chuyện cá nhân của người dùng đại lý
 */
@Data
public class AgentChatHistoryUserVO {
    @Schema(description = "聊天内容")
    private String content;

    @Schema(description = "音频ID")
    private String audioId;
}
