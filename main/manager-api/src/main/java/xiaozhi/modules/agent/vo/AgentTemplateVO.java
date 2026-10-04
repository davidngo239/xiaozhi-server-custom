package xiaozhi.modules.agent.vo;

import lombok.Data;
import lombok.EqualsAndHashCode;
import xiaozhi.modules.agent.entity.AgentTemplateEntity;

@Data
@EqualsAndHashCode(callSuper = true)
public class AgentTemplateVO extends AgentTemplateEntity {
    // Âm sắc nhân vật
    private String ttsModelName;

    // hình mẫu
    private String llmModelName;
}
