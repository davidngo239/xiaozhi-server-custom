package xiaozhi.modules.sys.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;

import org.apache.ibatis.annotations.Param;
import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.sys.entity.SysDictDataEntity;
import xiaozhi.modules.sys.vo.SysDictDataItem;

/**
 * dữ liệu từ điển
 */
@Mapper
public interface SysDictDataDao extends BaseDao<SysDictDataEntity> {

    List<SysDictDataItem> getDictDataByType(String dictType);

    /**
     * Nhận mã hóa loại từ điển dựa trên ID loại từ điển
     * 
     * @param dictTypeId ID loại từ điển
     * @return mã hóa kiểu từ điển
     */
    String getTypeByTypeId(Long dictTypeId);

    /**
     * Nhận bộ mã hóa loại từ điển dựa trên bộ ID dữ liệu từ điển
     */
    List<String> getDictTypesByIdList(@Param("dictDataIdList") List<Long> dictDataIdList);
}
