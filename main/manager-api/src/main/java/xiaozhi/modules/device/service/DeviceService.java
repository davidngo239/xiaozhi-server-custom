package xiaozhi.modules.device.service;

import java.util.Date;
import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.device.dto.DeviceManualAddDTO;
import xiaozhi.modules.device.dto.DevicePageUserDTO;
import xiaozhi.modules.device.dto.DeviceReportReqDTO;
import xiaozhi.modules.device.dto.DeviceReportRespDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.vo.UserShowDeviceListVO;

public interface DeviceService extends BaseService<DeviceEntity> {
    /**
     * Nhận dữ liệu trực tuyến của thiết bị
     */
    String getDeviceOnlineData(String agentId);

    /**
     * Kiểm tra xem thiết bị đã được kích hoạt chưa
     */
    DeviceReportRespDTO checkDeviceActive(String macAddress, String clientId,
            DeviceReportReqDTO deviceReport);

    /**
     * Lấy danh sách thiết bị của tác nhân do người dùng chỉ định,
     */
    List<DeviceEntity> getUserDevices(Long userId, String agentId);

    /**
     * Lấy danh sách thiết bị của tác nhân do người dùng chỉ định (có xử lý múi giờ),
     */
    List<UserShowDeviceListVO> getUserDeviceList(Long userId, String agentId);

    /**
     * Hủy liên kết thiết bị
     */
    void unbindDevice(Long userId, String deviceId);

    /**
     * Kích hoạt thiết bị
     */
    Boolean deviceActivation(String agentId, String activationCode);

    /**
     * Xóa tất cả thiết bị cho người dùng này
     * 
     * @param userId userid
     */
    void deleteByUserId(Long userId);

    /**
     * Xóa tất cả các thiết bị được liên kết với tác nhân được chỉ định
     * 
     * @param agentId id đại lý
     */
    void deleteByAgentId(String agentId);

    /**
     * Lấy số lượng thiết bị của một người dùng được chỉ định
     * 
     * @param userId userid
     * @return số lượng thiết bị
     */
    Long selectCountByUserId(Long userId);

    /**
     * Nhận tất cả thông tin thiết bị trong các trang
     *
     * @param dto tham số tìm kiếm phân trang
     * @return dữ liệu phân trang danh sách người dùng
     */
    PageData<UserShowDeviceListVO> page(DevicePageUserDTO dto);

    /**
     * Nhận thông tin thiết bị dựa trên địa chỉ MAC
     * 
     * @param macAddress chỉ địa chỉ MAC
     * @return thông tin thiết bị
     */
    DeviceEntity getDeviceByMacAddress(String macAddress);

    /**
     * Nhận mã kích hoạt dựa trên ID thiết bị
     * 
     * @param deviceId thiết bị ID thiết bị
     * @return mã kích hoạt
     */
    String geCodeByDeviceId(String deviceId);

    /**
     * Nhận thời gian kết nối gần đây nhất cho thiết bị thông minh này
     * 
     * @param agentId id đại lý
     * @return Trả về thời gian kết nối gần đây nhất của thiết bị
     */
    Date getLatestLastConnectionTime(String agentId);

    /**
     * Thêm thiết bị theo cách thủ công
     */
    void manualAddDevice(Long userId, DeviceManualAddDTO dto);

    /**
     * Cập nhật thông tin kết nối thiết bị
     */
    void updateDeviceConnectionInfo(String agentId, String deviceId, String appVersion);

    /**
     * Tạo mã thông báo xác thực WebSocket
     *
     * @param clientId ID máy khách
     * @param username người dùng tên người dùng (thường là deviceId)
     * @return chuỗi mã thông báo xác thực
     * @throws Exception lệ khi tạo mã thông báo
     */
    String generateWebSocketToken(String clientId, String username) throws Exception;

    /**
     * Tìm kiếm thiết bị dựa trên địa chỉ MAC
     *
     * @param macAddress Từ khóa địa chỉ MAC
     * @param userId ID người dùng
     * @return danh sách thiết bị
     */
    List<DeviceEntity> searchDevicesByMacAddress(String macAddress, Long userId);

    /**
     * Nhận danh sách công cụ thiết bị
     */
    Object getDeviceTools(String deviceId);

    /**
     * Công cụ thiết bị gọi
     */
    Object callDeviceTool(String deviceId, String toolName, Map<String, Object> arguments);

    }
