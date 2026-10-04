package xiaozhi.modules.agent.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Bảng ghi cuộc trò chuyện của đại lý
 *
 * @author Goody
 * @version 1.0, 2025/4/30
 * @since 1.0.0
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
@TableName(value = "ai_agent_chat_history")
public class AgentChatHistoryEntity {
    /**
     * ID khóa chính
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * Địa chỉ MAC
     */
    @TableField(value = "mac_address")
    private String macAddress;

    /**
     * Mã đại lý
     */
    @TableField(value = "agent_id")
    private String agentId;

    /**
     * ID phiên
     */
    @TableField(value = "session_id")
    private String sessionId;

    /**
     * Loại tin nhắn: 1-Người dùng, 2-Agent
     */
    @TableField(value = "chat_type")
    private Byte chatType;

    /**
     * Nội dung trò chuyện
     */
    @TableField(value = "content")
    private String content;

    /**
     * Dữ liệu âm thanh base64
     */
    @TableField(value = "audio_id")
    private String audioId;

    /**
     * thời gian sáng tạo
     */
    @TableField(value = "created_at")
    private Date createdAt;

    /**
     * Thời gian cập nhật
     */
    @TableField(value = "updated_at")
    private Date updatedAt;
}
