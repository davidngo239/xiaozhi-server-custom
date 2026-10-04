package xiaozhi.modules.agent.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;

/**
 * Bảng dữ liệu âm thanh trò chuyện của đại lý
 *
 * @author Goody
 * @version 1.0, 2025/5/8
 * @since 1.0.0
 */
@Data
@TableName("ai_agent_chat_audio")
public class AgentChatAudioEntity {
    /**
     * ID khóa chính
     */
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    /**
     * dữ liệu tác phẩm âm thanh
     */
    private byte[] audio;
}