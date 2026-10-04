package xiaozhi.modules.sys.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.sys.dto.SysDictTypeDTO;
import xiaozhi.modules.sys.entity.SysDictTypeEntity;
import xiaozhi.modules.sys.vo.SysDictTypeVO;

/**
 * từ điển dữ liệu
 */
public interface SysDictTypeService extends BaseService<SysDictTypeEntity> {

    /**
     * Truy vấn thông tin loại từ điển theo trang
     *
     * @param params số truy vấn, bao gồm thông tin phân trang và điều kiện truy vấn
     * @return trả về dữ liệu loại từ điển được phân trang
     */
    PageData<SysDictTypeVO> page(Map<String, Object> params);

    /**
     * Nhận thông tin loại từ điển dựa trên ID
     *
     * @param id ID loại từ điển
     * @return Trả về một đối tượng kiểu từ điển
     */
    SysDictTypeVO get(Long id);

    /**
     * Lưu thông tin loại từ điển
     *
     * @param dto đối tượng truyền dữ liệu kiểu từ điển
     */
    void save(SysDictTypeDTO dto);

    /**
     * Cập nhật thông tin loại từ điển
     *
     * @param dto đối tượng truyền dữ liệu kiểu từ điển
     */
    void update(SysDictTypeDTO dto);

    /**
     * Xóa thông tin loại từ điển
     *
     * @param ids mảng ID loại từ điển sẽ bị xóa
     */
    void delete(Long[] ids);

    /**
     * Liệt kê tất cả thông tin loại từ điển
     *
     * @return Trả về danh sách loại từ điển
     */
    List<SysDictTypeVO> list(Map<String, Object> params);
}