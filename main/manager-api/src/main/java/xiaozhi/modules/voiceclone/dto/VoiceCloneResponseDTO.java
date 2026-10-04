package xiaozhi.modules.voiceclone.dto;

import java.util.Date;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * Phản hồi nhân bản âm thanh DTO
 * Được sử dụng để hiển thị thông tin bản sao âm thanh ở mặt trước, bao gồm tên model và tên người dùng
 */
@Data
@Schema(description = "声音克隆响应DTO")
public class VoiceCloneResponseDTO {

    @Schema(description = "唯一标识")
    private String id;

    @Schema(description = "声音名称")
    private String name;

    @Schema(description = "模型id")
    private String modelId;

    @Schema(description = "模型名称")
    private String modelName;

    @Schema(description = "声音id")
    private String voiceId;

    @Schema(description = "语言")
    private String languages;

    @Schema(description = "用户ID（关联用户表）")
    private Long userId;

    @Schema(description = "用户名称")
    private String userName;

    @Schema(description = "训练状态：0待训练 1训练中 2训练成功 3训练失败")
    private Integer trainStatus;

    @Schema(description = "训练错误原因")
    private String trainError;

    @Schema(description = "创建时间")
    private Date createDate;

    @Schema(description = "是否有音频数据")
    private Boolean hasVoice;
}