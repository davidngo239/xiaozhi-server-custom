package xiaozhi.modules.device.dto;

import lombok.Data;

@Data
public class DeviceManualAddDTO {
    private String agentId;
    private String board;        // Mẫu thiết bị
    private String appVersion;   // Phiên bản phần mềm
    private String macAddress;   // Địa chỉ Mac
} 