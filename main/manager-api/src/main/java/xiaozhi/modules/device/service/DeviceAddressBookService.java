package xiaozhi.modules.device.service;

import java.util.List;
import java.util.Map;

import xiaozhi.modules.device.entity.DeviceAddressBookEntity;

public interface DeviceAddressBookService {

    /**
     * Lấy danh sách sổ địa chỉ thiết bị
     */
    List<DeviceAddressBookEntity> getAddressBookList(String macAddress);

    /**
     * Nhận sổ địa chỉ của tất cả các thiết bị (đối với bộ nhớ đệm toàn cầu)
     */
    Map<String, Map<String, String>> getAllAddressBooks();

    /**
     * Cập nhật bí danh
     */
    void updateAlias(String macAddress, String targetMac, String alias);

    /**
     * Cập nhật quyền
     */
    void updatePermission(String macAddress, String targetMac, Boolean hasPermission);

    /**
     * Thêm hoặc cập nhật bản ghi sổ địa chỉ
     */
    void saveOrUpdate(String macAddress, String targetMac, String alias, Boolean hasPermission);

    /**
     * Làm mới bộ đệm sổ địa chỉ
     */
    void refreshCache();

    /**
     * Thực hiện cuộc gọi dựa trên biệt danh
     * @param callerMac gọiMac địa chỉ MAC của bên gọi
     * @param nickname danh Biệt hiệu của bên được gọi
     * @param isAnswer Liệu nó có ở chế độ trả lời hay không (bỏ qua kiểm tra quyền)
     */
    Map<String, Object> callByNickname(String callerMac, String nickname, boolean isAnswer);

    /**
     * Xóa hàng loạt bản ghi sổ địa chỉ liên quan đến thiết bị
     */
    void deleteByMacAddresses(List<String> macAddresses);
}