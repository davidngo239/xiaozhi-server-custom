package xiaozhi.modules.model.dto;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "音色信息")
public class VoiceDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    @Schema(description = "音色ID")
    private String id;

    @Schema(description = "音色名称")
    private String name;

    @Schema(description = "音频播放地址")
    private String voiceDemo;
    
    @Schema(description = "语言类型")
    private String languages;
    
    @Schema(description = "是否为克隆音色")
    private Boolean isClone;

    // Thêm hàm tạo hai tham số để duy trì khả năng tương thích ngược
    public VoiceDTO(String id, String name) {
        this.id = id;
        this.name = name;
        this.voiceDemo = null;
        this.languages = null;
        this.isClone = false; // Không được sao chép theo mặc định
    }
    
    // Đã thêm hàm tạo ba tham số cho âm sắc thông thường
    public VoiceDTO(String id, String name, String voiceDemo) {
        this.id = id;
        this.name = name;
        this.voiceDemo = voiceDemo;
        this.languages = null;
        this.isClone = false;
    }

}