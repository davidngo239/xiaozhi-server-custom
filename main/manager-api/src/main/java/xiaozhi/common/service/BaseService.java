package xiaozhi.common.service;

import java.io.Serializable;
import java.util.Collection;

import com.baomidou.mybatisplus.core.conditions.Wrapper;

/**
 * Giao diện dịch vụ cơ bản, tất cả các giao diện Dịch vụ phải kế thừa
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
public interface BaseService<T> {
    Class<T> currentModelClass();

    /**
     * <p>
     * Chèn bản ghi (chọn trường, chèn theo chiến lược)
     * </p>
     *
     * @param entity tượng thực thể thực thể
     */
    boolean insert(T entity);

    /**
     * <p>
     * Insert (batch), phương pháp này không hỗ trợ Oracle, SQL Server
     * </p>
     *
     * @param entityList sưu tập đối tượng thực thể danh sách thực thể
     */
    boolean insertBatch(Collection<T> entityList);

    /**
     * <p>
     * Insert (batch), phương pháp này không hỗ trợ Oracle, SQL Server
     * </p>
     *
     * @param entityList sưu tập đối tượng thực thể danh sách thực thể
     * @param batchSize chèn kích thước lô
     */
    boolean insertBatch(Collection<T> entityList, int batchSize);

    /**
     * <p>
     * Chọn chỉnh sửa dựa trên ID
     * </p>
     *
     * @param entity tượng thực thể thực thể
     */
    boolean updateById(T entity);

    /**
     * <p>
     * Cập nhật bản ghi dựa trên điều kiện WhereEntity
     * </p>
     *
     * @param entity tượng thực thể thực thể
     * @param updateWrapper Lớp hoạt động đóng gói đối tượng thực thể
     *                      {@link com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper}
     */
    boolean update(T entity, Wrapper<T> updateWrapper);

    /**
     * <p>
     * Cập nhật hàng loạt dựa trên ID
     * </p>
     *
     * @param entityList sưu tập đối tượng thực thể danh sách thực thể
     */
    boolean updateBatchById(Collection<T> entityList);

    /**
     * <p>
     * Cập nhật hàng loạt dựa trên ID
     * </p>
     *
     * @param entityList sưu tập đối tượng thực thể danh sách thực thể
     * @param batchSize cập nhật kích thước lô
     */
    boolean updateBatchById(Collection<T> entityList, int batchSize);

    /**
     * <p>
     * Truy vấn theo ID
     * </p>
     *
     * @param id ID khóa chính
     */
    T selectById(Serializable id);

    /**
     * <p>
     * Xóa theo ID
     * </p>
     *
     * @param id ID khóa chính
     */
    boolean deleteById(Serializable id);

    /**
     * <p>
     * Xóa (xóa hàng loạt dựa trên ID)
     * </p>
     *
     * @param idList danh sách ID khóa chính
     */
    boolean deleteBatchIds(Collection<? extends Serializable> idList);
}