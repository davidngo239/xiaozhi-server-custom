package xiaozhi.modules.config.service;

import java.util.List;
import java.util.Map;

public interface ConfigService {
    /**
     * Nhận cấu hình máy chủ
     *
     * @param isCache có lưu vào bộ nhớ đệm không
     * @return thông tin cấu hình
     */
    Map<String, Object> getConfig(Boolean isCache);

    /**
     * Nhận cấu hình mô hình đại lý
     *
     * @param macAddress chỉ địa chỉ MAC
     * @param selectedModule Các mô hình đã được máy khách khởi tạo
     * @return thông tin cấu hình mô hình
     */
    Map<String, Object> getAgentModels(String macAddress, Map<String, String> selectedModule);

    /**
     * Nhận từ thay thế đại lý
     *
     * @param macAddress chỉ MAC của thiết bị
     * @return Danh sách từ thay thế, định dạng như ["Mẫu 1|Mẫu 01", "Mẫu 2|Mẫu 02"]
     */
    List<String> getCorrectWords(String macAddress);
}
