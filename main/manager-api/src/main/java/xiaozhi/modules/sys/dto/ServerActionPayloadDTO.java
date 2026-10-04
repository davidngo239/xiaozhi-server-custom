package xiaozhi.modules.sys.dto;

import lombok.Data;
import xiaozhi.modules.sys.enums.ServerActionEnum;

import java.util.Map;

/**
 * Máy chủ hành động DTO
 */
@Data
public class ServerActionPayloadDTO
{
    /**
    * Loại (thứ mà bảng điều khiển thông minh gửi đến máy chủ là máy chủ)
    */
    private String type;
    /**
    * hành động
    */
    private ServerActionEnum action;
    /**
    * nội dung
    */
    private Map<String, Object> content;

    public static ServerActionPayloadDTO build(ServerActionEnum action, Map<String, Object> content) {
        ServerActionPayloadDTO serverActionPayloadDTO = new ServerActionPayloadDTO();
        serverActionPayloadDTO.setAction(action);
        serverActionPayloadDTO.setContent(content);
        serverActionPayloadDTO.setType("server");
        return serverActionPayloadDTO;
    }
    // Tư nhân hóa
    private ServerActionPayloadDTO() {}
}
