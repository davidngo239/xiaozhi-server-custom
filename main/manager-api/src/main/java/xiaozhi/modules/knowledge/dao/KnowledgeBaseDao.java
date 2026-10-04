package xiaozhi.modules.knowledge.dao;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.knowledge.entity.KnowledgeBaseEntity;

/**
 * Cơ sở kiến thứcCơ sở kiến thức
 */
@Mapper
public interface KnowledgeBaseDao extends BaseDao<KnowledgeBaseEntity> {

    /**
     * Xóa các bản ghi ánh xạ plug-in liên quan dựa trên ID cơ sở kiến thức
     * 
     * @param knowledgeBaseId ID cơ sở kiến thức
     */
    void deletePluginMappingByKnowledgeBaseId(@Param("knowledgeBaseId") String knowledgeBaseId);

    /**
     * Thứ nguyên chung Cập nhật nguyên tử Thống kê cơ sở kiến thức
     * 
     * @param datasetId dữ liệuId ID tập dữ liệu
     * @param docDelta tăng số tài liệu
     * @param chunkDelta tăng số đoạn
     * @param tokenDelta Tăng số lượng mã thông báo
     */
    void updateStatsAfterChange(@Param("datasetId") String datasetId,
            @Param("docDelta") Integer docDelta,
            @Param("chunkDelta") Long chunkDelta,
            @Param("tokenDelta") Long tokenDelta);

}