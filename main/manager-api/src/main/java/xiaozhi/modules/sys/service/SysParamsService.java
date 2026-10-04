package xiaozhi.modules.sys.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.sys.dto.SysParamsDTO;
import xiaozhi.modules.sys.entity.SysParamsEntity;

/**
 * Quản lý thông số
 */
public interface SysParamsService extends BaseService<SysParamsEntity> {

    PageData<SysParamsDTO> page(Map<String, Object> params);

    List<SysParamsDTO> list(Map<String, Object> params);

    SysParamsDTO get(Long id);

    void save(SysParamsDTO dto);

    void update(SysParamsDTO dto);

    void delete(String[] ids);

    /**
     * Lấy giá trị của tham số dựa trên mã hóa tham số
     *
     * @param paramCode hóa tham số paramCode
     * @param fromCache Có lấy được từ bộ đệm hay không
     */
    String getValue(String paramCode, Boolean fromCache);

    /**
     * Theo mã hóa tham số, lấy đối tượng Object có giá trị
     *
     * @param paramCode hóa tham số paramCode
     * @param clazz Đối tượng
     */
    <T> T getValueObject(String paramCode, Class<T> clazz);

    /**
     * Cập nhật giá trị theo mã hóa tham số
     *
     * @param paramCode hóa tham số paramCode
     * @param paramValue trị tham số paramValue
     */
    int updateValueByCode(String paramCode, String paramValue);

    /**
     * Khởi tạo khóa máy chủ
     */
    void initServerSecret();

    /**
     * Nhận cấu hình menu chức năng hệ thống
     *
     * @param fromCache Có lấy được từ bộ đệm hay không
     * @return Cấu hình menu chức năng hệ thống Chuỗi JSON
     */
    String getSystemWebMenu(boolean fromCache);

    /**
     * Cập nhật cấu hình menu chức năng hệ thống (tự động xử lý việc dọn dẹp plug-in liên quan đến chức năng)
     *
     * @param configJson Cấu hình menu chức năng hệ thống mới JSON
     */
    void updateSystemWebMenu(String configJson);
}
