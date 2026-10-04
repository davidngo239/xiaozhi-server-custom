package xiaozhi.modules.agent.vo;

import lombok.Data;

import java.util.Date;

/**
 * Hiển thị danh sách giọng nói của đại lý VO
 */
@Data
public class AgentVoicePrintVO {

    /**
     * id khóa chính
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
    /**
     * thời gian sáng tạo
     */
    private Date createDate;
}
