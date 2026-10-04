package xiaozhi.modules.model.dto;

import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * Dữ liệu hiển thị cơ bản của mô hình LLM
 */
@EqualsAndHashCode(callSuper = true)
@Data
public class LlmModelBasicInfoDTO extends ModelBasicInfoDTO{
    private String type;
}