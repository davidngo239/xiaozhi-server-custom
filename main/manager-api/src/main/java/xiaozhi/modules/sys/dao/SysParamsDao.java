package xiaozhi.modules.sys.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.sys.entity.SysParamsEntity;

/**
 * Quản lý thông số
 */
@Mapper
public interface SysParamsDao extends BaseDao<SysParamsEntity> {
    /**
     * Giá trị truy vấn dựa trên mã hóa tham số
     *
     * @param paramCode hóa tham số paramCode
     * @return giá trị tham số
     */
    String getValueByCode(String paramCode);

    /**
     * Nhận danh sách mã hóa tham số
     *
     * @param ids ids
     * @return trả về danh sách mã hóa tham số
     */
    List<String> getParamCodeList(String[] ids);

    /**
     * Cập nhật giá trị theo mã hóa tham số
     *
     * @param paramCode hóa tham số paramCode
     * @param paramValue trị tham số paramValue
     */
    int updateValueByCode(@Param("paramCode") String paramCode, @Param("paramValue") String paramValue);
}
