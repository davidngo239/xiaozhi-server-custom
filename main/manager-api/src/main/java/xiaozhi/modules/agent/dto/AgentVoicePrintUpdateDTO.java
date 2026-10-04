package xiaozhi.modules.agent.dto;

import lombok.Data;

/**
 * Sửa đổi dto của giọng nói của tổng đài viên
 *
 * @author zjy
 */
@Data
public class AgentVoicePrintUpdateDTO {
    /**
     * ID giọng nói thông minh
     */
    private String id;
    /**
     * id tập tin âm thanh
     */
    private String audioId;
    /**
     * Tên của người có giọng nói đến từ
     */
    private String sourceName;
    /**
     * Người mô tả nguồn gốc của giọng nói
     */
    private String introduce;
}
