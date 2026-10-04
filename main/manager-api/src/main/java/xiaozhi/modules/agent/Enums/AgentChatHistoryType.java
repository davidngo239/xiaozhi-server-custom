package xiaozhi.modules.agent.Enums;


import lombok.Getter;

/**
 * Loại bản ghi trò chuyện của tổng đài viên
 */
@Getter
public enum AgentChatHistoryType {

    USER((byte) 1),
    AGENT((byte) 2);

    private final byte value;

    AgentChatHistoryType(byte i) {
        this.value = i;
    }

}
