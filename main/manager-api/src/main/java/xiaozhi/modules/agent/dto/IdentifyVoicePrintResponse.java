package xiaozhi.modules.agent.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

/**
 * Đối tượng được trả về bởi giao diện nhận dạng giọng nói
 */
@Data
public class IdentifyVoicePrintResponse {
    /**
     * Id giọng nói phù hợp nhất
     */
    @JsonProperty("speaker_id")
    private String speakerId;
    /**
     * Điểm giọng nói
     */
    private Double score;
}
