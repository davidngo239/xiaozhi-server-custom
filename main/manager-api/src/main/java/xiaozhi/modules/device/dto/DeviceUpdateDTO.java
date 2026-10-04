package xiaozhi.modules.device.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.io.Serializable;

/**
 * Cập nhật thiết bị DTO
 */
@Data
public class DeviceUpdateDTO implements Serializable {
    /**
    * Tự động cập nhật trạng thái
    */
    @Max(1)
    @Min(0)
    private Integer autoUpdate;

    /**
    * Bí danh thiết bị
    */
    @Size(max = 64)
    private String alias;

    private static final long serialVersionUID = 1L;
}
