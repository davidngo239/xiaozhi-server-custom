package xiaozhi.modules.sys.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.sys.dto.SysDictDataDTO;
import xiaozhi.modules.sys.entity.SysDictDataEntity;
import xiaozhi.modules.sys.vo.SysDictDataItem;
import xiaozhi.modules.sys.vo.SysDictDataVO;

/**
 * từ điển dữ liệu
 */
public interface SysDictDataService extends BaseService<SysDictDataEntity> {

    /**
     * Truy vấn thông tin từ điển dữ liệu theo trang
     *
     * @param params số truy vấn, bao gồm thông tin phân trang và điều kiện truy vấn
     * @return Trả về kết quả truy vấn phân trang của từ điển dữ liệu
     */
    PageData<SysDictDataVO> page(Map<String, Object> params);

    /**
     * Nhận thực thể từ điển dữ liệu dựa trên ID
     *
     * @param id mã định danh duy nhất của thực thể từ điển dữ liệu
     * @return Trả về chi tiết của thực thể từ điển dữ liệu
     */
    SysDictDataVO get(Long id);

    /**
     * Lưu mục từ điển dữ liệu mới
     *
     * @param dto Đối tượng truyền dữ liệu đã lưu của mục từ điển dữ liệu
     */
    void save(SysDictDataDTO dto);

    /**
     * Cập nhật mục từ điển dữ liệu
     *
     * @param dto cập nhật đối tượng truyền dữ liệu của mục từ điển dữ liệu
     */
    void update(SysDictDataDTO dto);

    /**
     * Xóa mục từ điển dữ liệu
     *
     * @param ids Mảng ID của các mục từ điển dữ liệu sẽ bị xóa
     */
    void delete(Long[] ids);

    /**
     * Xóa dữ liệu từ điển tương ứng theo ID loại từ điển
     *
     * @param dictTypeId ID loại từ điển
     */
    void deleteByTypeId(Long dictTypeId);

    /**
     * Nhận danh sách dữ liệu từ điển dựa trên loại từ điển
     *
     * @param dictType loại từ điển
     * @return trả về danh sách dữ liệu từ điển
     */
    List<SysDictDataItem> getDictDataByType(String dictType);

}