package xiaozhi.modules.knowledge.dao;

import org.apache.ibatis.annotations.Mapper;
import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.knowledge.entity.DocumentEntity;

/**
 * Tài liệu DAO
 */
@Mapper
public interface DocumentDao extends BaseDao<DocumentEntity> {
}
