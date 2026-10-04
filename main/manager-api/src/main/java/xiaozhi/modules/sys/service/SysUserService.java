package xiaozhi.modules.sys.service;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.sys.dto.AdminPageUserDTO;
import xiaozhi.modules.sys.dto.PasswordDTO;
import xiaozhi.modules.sys.dto.SysUserDTO;
import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.vo.AdminPageUserVO;

/**
 * người dùng hệ thống
 */
public interface SysUserService extends BaseService<SysUserEntity> {

    SysUserDTO getByUsername(String username);

    SysUserDTO getByUserId(Long userId);

    void save(SysUserDTO dto);

    /**
     * Xóa người dùng được chỉ định và các thiết bị và tác nhân dữ liệu liên quan
     * 
     * @param ids
     */
    void deleteById(Long ids);

    /**
     * Xác minh xem có cho phép thay đổi mật khẩu hay không
     * 
     * @param userId userid
     * @param passwordDTO Tham số xác minh mật khẩu
     */
    void changePassword(Long userId, PasswordDTO passwordDTO);

    /**
     * Thay đổi mật khẩu trực tiếp mà không cần xác minh
     * 
     * @param userId userid
     * @param password khẩu mật khẩu
     */
    void changePasswordDirectly(Long userId, String password);

    /**
     * đặt lại mật khẩu
     * 
     * @param userId userid
     * @return tạo ngẫu nhiên mật khẩu phù hợp với thông số kỹ thuật
     */
    String resetPassword(Long userId);

    /**
     * Quản trị viên phân trang thông tin người dùng
     * 
     * @param dto tham số tìm kiếm phân trang
     * @return dữ liệu phân trang danh sách người dùng
     */
    PageData<AdminPageUserVO> page(AdminPageUserDTO dto);

    /**
     * Sửa đổi trạng thái người dùng theo đợt
     * 
     * @param status thái trạng thái người dùng
     * @param userIds mảng ID người dùng
     */
    void changeStatus(Integer status, String[] userIds);

    /**
     * Nhận liệu đăng ký người dùng có được phép hay không
     * 
     * @return xem có cho phép đăng ký người dùng hay không
     */
    boolean getAllowUserRegister();
}
