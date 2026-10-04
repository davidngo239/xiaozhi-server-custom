package xiaozhi.modules.knowledge.controller;

import java.util.*;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import cn.hutool.core.collection.CollUtil;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.knowledge.dto.KnowledgeBaseDTO;
import xiaozhi.modules.knowledge.service.KnowledgeBaseService;
import xiaozhi.modules.knowledge.service.KnowledgeManagerService;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.security.user.SecurityUser;

@AllArgsConstructor
@RestController
@RequestMapping("/datasets")
@Tag(name = "知识库管理")
public class KnowledgeBaseController {

    private final KnowledgeBaseService knowledgeBaseService;
    private final KnowledgeManagerService knowledgeManagerService;

    @GetMapping
    @Operation(summary = "分页查询知识库列表")
    @RequiresPermissions("sys:role:normal")
    public Result<PageData<KnowledgeBaseDTO>> getPageList(
            @RequestParam(required = false) String name,
            @RequestParam(required = false, defaultValue = "1") Integer page,
            @RequestParam(required = false, defaultValue = "10") Integer page_size) {
        // Lấy ID người dùng đã đăng nhập hiện tại
        Long currentUserId = SecurityUser.getUserId();

        KnowledgeBaseDTO knowledgeBaseDTO = new KnowledgeBaseDTO();
        knowledgeBaseDTO.setName(name);
        knowledgeBaseDTO.setCreator(currentUserId); // Đặt ID người tạo để lọc quyền

        PageData<KnowledgeBaseDTO> pageData = knowledgeBaseService.getPageList(knowledgeBaseDTO, page, page_size);
        return new Result<PageData<KnowledgeBaseDTO>>().ok(pageData);
    }

    @GetMapping("/{dataset_id}")
    @Operation(summary = "根据知识库ID获取知识库详情")
    @RequiresPermissions("sys:role:normal")
    public Result<KnowledgeBaseDTO> getByDatasetId(@PathVariable("dataset_id") String datasetId) {
        // Lấy ID người dùng đã đăng nhập hiện tại
        Long currentUserId = SecurityUser.getUserId();

        KnowledgeBaseDTO knowledgeBaseDTO = knowledgeBaseService.getByDatasetId(datasetId);

        // Kiểm tra quyền: Người dùng chỉ có thể xem cơ sở kiến thức do chính họ tạo ra
        if (knowledgeBaseDTO.getCreator() == null || !knowledgeBaseDTO.getCreator().equals(currentUserId)) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }

        return new Result<KnowledgeBaseDTO>().ok(knowledgeBaseDTO);
    }

    @PostMapping
    @Operation(summary = "创建知识库")
    @RequiresPermissions("sys:role:normal")
    public Result<KnowledgeBaseDTO> save(@RequestBody @Validated KnowledgeBaseDTO knowledgeBaseDTO) {
        KnowledgeBaseDTO resp = knowledgeBaseService.save(knowledgeBaseDTO);
        return new Result<KnowledgeBaseDTO>().ok(resp);
    }

    @PutMapping("/{dataset_id}")
    @Operation(summary = "更新知识库")
    @RequiresPermissions("sys:role:normal")
    public Result<KnowledgeBaseDTO> update(@PathVariable("dataset_id") String datasetId,
            @RequestBody @Validated KnowledgeBaseDTO knowledgeBaseDTO) {
        // Lấy ID người dùng đã đăng nhập hiện tại
        Long currentUserId = SecurityUser.getUserId();

        // Trước tiên hãy lấy thông tin cơ sở kiến thức hiện có để kiểm tra quyền
        KnowledgeBaseDTO existingKnowledgeBase = knowledgeBaseService.getByDatasetId(datasetId);

        // Kiểm tra quyền: Người dùng chỉ có thể cập nhật cơ sở kiến thức do chính họ tạo ra
        if (existingKnowledgeBase.getCreator() == null || !existingKnowledgeBase.getCreator().equals(currentUserId)) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }

        // [CỐ ĐỊNH] Chèn ID để ngăn lớp Dịch vụ không tìm thấy bản ghi
        knowledgeBaseDTO.setId(existingKnowledgeBase.getId());
        knowledgeBaseDTO.setDatasetId(datasetId);
        KnowledgeBaseDTO resp = knowledgeBaseService.update(knowledgeBaseDTO);
        return new Result<KnowledgeBaseDTO>().ok(resp);
    }

    @DeleteMapping("/{dataset_id}")
    @Operation(summary = "删除单个知识库")
    @Parameter(name = "dataset_id", description = "知识库ID", required = true)
    @RequiresPermissions("sys:role:normal")
    public Result<Void> delete(@PathVariable("dataset_id") String datasetId) {
        // Lấy ID người dùng đã đăng nhập hiện tại
        Long currentUserId = SecurityUser.getUserId();

        // Trước tiên hãy lấy thông tin cơ sở kiến thức hiện có để kiểm tra quyền
        KnowledgeBaseDTO existingKnowledgeBase = knowledgeBaseService.getByDatasetId(datasetId);

        // Kiểm tra quyền: Người dùng chỉ được xóa cơ sở tri thức do chính mình tạo ra
        if (existingKnowledgeBase.getCreator() == null || !existingKnowledgeBase.getCreator().equals(currentUserId)) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }

        // [Sửa lỗi kiến trúc] Ngăn chặn dữ liệu mồ côi và giải quyết các phụ thuộc vòng tròn thông qua việc xóa xếp tầng lớp điều phối
        knowledgeManagerService.deleteDatasetWithFiles(datasetId);
        return new Result<>();
    }

    @DeleteMapping("/batch")
    @Operation(summary = "批量删除知识库")
    @Parameter(name = "ids", description = "知识库ID列表，用逗号分隔", required = true)
    @RequiresPermissions("sys:role:normal")
    public Result<Void> deleteBatch(@RequestParam("ids") String ids) {
        if (StringUtils.isBlank(ids)) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }

        // Lấy ID người dùng đã đăng nhập hiện tại
        Long currentUserId = SecurityUser.getUserId();
        List<String> idList = Arrays.asList(ids.split(","));
        List<KnowledgeBaseDTO> knowledgeBaseDTOs = Optional.ofNullable(knowledgeBaseService.getByDatasetIdList(idList))
                .orElseGet(ArrayList::new);
        if (CollUtil.isNotEmpty(knowledgeBaseDTOs)) {
            knowledgeBaseDTOs.forEach(item -> {
                // Kiểm tra quyền: Người dùng chỉ được xóa cơ sở tri thức do chính mình tạo ra
                if (item.getCreator() == null || !item.getCreator().equals(currentUserId)) {
                    throw new RenException(ErrorCode.NO_PERMISSION);
                }
                // [Sửa lỗi kiến trúc] Loại bỏ xếp tầng thông qua cấp độ điều phối
                knowledgeManagerService.deleteDatasetWithFiles(item.getDatasetId());
            });
        }
        return new Result<>();
    }

    @GetMapping("/rag-models")
    @Operation(summary = "获取RAG模型列表")
    @RequiresPermissions("sys:role:normal")
    public Result<List<ModelConfigEntity>> getRAGModels() {
        List<ModelConfigEntity> result = knowledgeBaseService.getRAGModels();
        return new Result<List<ModelConfigEntity>>().ok(result);
    }
}
