package xiaozhi.modules.sys.controller;

import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.Parameters;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.annotation.LogOperation;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.AssertUtils;
import xiaozhi.common.validator.ValidatorUtils;
import xiaozhi.common.validator.group.AddGroup;
import xiaozhi.common.validator.group.DefaultGroup;
import xiaozhi.common.validator.group.UpdateGroup;
import xiaozhi.modules.config.service.ConfigService;
import xiaozhi.modules.sys.dto.SysParamsDTO;
import xiaozhi.modules.sys.service.SysParamsService;
import xiaozhi.modules.sys.utils.WebSocketValidator;

/**
 * Quản lý thông số
 *
 * @author Mark sunlightcs@gmail.com
 * @since 1.0.0
 */
@RestController
@RequestMapping("admin/params")
@Tag(name = "参数管理")
@AllArgsConstructor
public class SysParamsController {
    private final SysParamsService sysParamsService;
    private final ConfigService configService;
    private final RestTemplate restTemplate;

    @GetMapping("page")
    @Operation(summary = "分页")
    @Parameters({
            @Parameter(name = Constant.PAGE, description = "当前页码，从1开始", in = ParameterIn.QUERY, required = true, ref = "int"),
            @Parameter(name = Constant.LIMIT, description = "每页显示记录数", in = ParameterIn.QUERY, required = true, ref = "int"),
            @Parameter(name = Constant.ORDER_FIELD, description = "排序字段", in = ParameterIn.QUERY, ref = "String"),
            @Parameter(name = Constant.ORDER, description = "排序方式，可选值(asc、desc)", in = ParameterIn.QUERY, ref = "String"),
            @Parameter(name = "paramCode", description = "参数编码或参数备注", in = ParameterIn.QUERY, ref = "String")
    })
    @RequiresPermissions("sys:role:superAdmin")
    public Result<PageData<SysParamsDTO>> page(@Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        PageData<SysParamsDTO> page = sysParamsService.page(params);

        return new Result<PageData<SysParamsDTO>>().ok(page);
    }

    @GetMapping("{id}")
    @Operation(summary = "信息")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<SysParamsDTO> get(@PathVariable("id") Long id) {
        SysParamsDTO data = sysParamsService.get(id);

        return new Result<SysParamsDTO>().ok(data);
    }

    @PostMapping
    @Operation(summary = "保存")
    @LogOperation("保存")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> save(@RequestBody SysParamsDTO dto) {
        // Dữ liệu hiệu quả
        ValidatorUtils.validateEntity(dto, AddGroup.class, DefaultGroup.class);

        sysParamsService.save(dto);
        configService.getConfig(false);
        return new Result<Void>();
    }

    @PutMapping
    @Operation(summary = "修改")
    @LogOperation("修改")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> update(@RequestBody SysParamsDTO dto) {
        // Dữ liệu hiệu quả
        ValidatorUtils.validateEntity(dto, UpdateGroup.class, DefaultGroup.class);

        // Xác minh danh sách địa chỉ WebSocket
        validateWebSocketUrls(dto.getParamCode(), dto.getParamValue());

        // Xác minh địa chỉ OTA
        validateOtaUrl(dto.getParamCode(), dto.getParamValue());

        // Xác minh địa chỉ MCP
        validateMcpUrl(dto.getParamCode(), dto.getParamValue());

        // Xác minh địa chỉ giọng nói
        validateVoicePrint(dto.getParamCode(), dto.getParamValue());

        // Xác minh độ dài khóa mqtt
        validateMqttSecretLength(dto.getParamCode(), dto.getParamValue());

        // Nếu đó là cấu hình menu chức năng hệ thống, hãy sử dụng quy trình xử lý đặc biệt
        if (Constant.SYSTEM_WEB_MENU.equals(dto.getParamCode())) {
            sysParamsService.updateSystemWebMenu(dto.getParamValue());
        } else {
            sysParamsService.update(dto);
        }
        configService.getConfig(false);
        return new Result<Void>();
    }

    /**
     * Xác minh danh sách địa chỉ WebSocket
     *
     * @param urls Danh sách địa chỉ WebSocket, được phân tách bằng dấu chấm phẩy
     * @return kết quả xác minh
     */
    private void validateWebSocketUrls(String paramCode, String urls) {
        if (!paramCode.equals(Constant.SERVER_WEBSOCKET)) {
            return;
        }
        String[] wsUrls = urls.split("\\;");
        if (wsUrls.length == 0) {
            throw new RenException(ErrorCode.WEBSOCKET_URLS_EMPTY);
        }
        for (String url : wsUrls) {
            if (StringUtils.isNotBlank(url)) {
                // Kiểm tra xem có bao gồm localhost hoặc 127.0.0.1 không
                if (url.contains("localhost") || url.contains("127.0.0.1")) {
                    throw new RenException(ErrorCode.WEBSOCKET_URL_LOCALHOST);
                }

                // Xác minh định dạng địa chỉ WebSocket
                if (!WebSocketValidator.validateUrlFormat(url)) {
                    throw new RenException(ErrorCode.WEBSOCKET_URL_FORMAT_ERROR);
                }

                // Kiểm tra kết nối WebSocket
                if (!WebSocketValidator.testConnection(url)) {
                    throw new RenException(ErrorCode.WEBSOCKET_CONNECTION_FAILED);
                }
            }
        }
    }

    @PostMapping("/delete")
    @Operation(summary = "删除")
    @LogOperation("删除")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> delete(@RequestBody String[] ids) {
        // Dữ liệu hiệu quả
        AssertUtils.isArrayEmpty(ids, "id");

        sysParamsService.delete(ids);
        configService.getConfig(false);
        return new Result<Void>();
    }

    /**
     * Xác minh địa chỉ OTA
     */
    private void validateOtaUrl(String paramCode, String url) {
        if (!paramCode.equals(Constant.SERVER_OTA)) {
            return;
        }
        if (StringUtils.isBlank(url) || url.equals("null")) {
            return;
        }

        // Kiểm tra xem có bao gồm localhost hoặc 127.0.0.1 không
        if (url.contains("localhost") || url.contains("127.0.0.1")) {
            throw new RenException(ErrorCode.OTA_URL_LOCALHOST);
        }

        // Xác minh định dạng URL
        if (!url.toLowerCase().startsWith("http")) {
            throw new RenException(ErrorCode.OTA_URL_PROTOCOL_ERROR);
        }
        if (!url.endsWith("/ota/")) {
            throw new RenException(ErrorCode.OTA_URL_FORMAT_ERROR);
        }

        try {
            // Gửi yêu cầu NHẬN
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            if (response.getStatusCode() != HttpStatus.OK) {
                throw new RenException(ErrorCode.OTA_INTERFACE_ACCESS_FAILED);
            }
            // Kiểm tra xem nội dung phản hồi có chứa thông tin liên quan đến OTA hay không
            String body = response.getBody();
            if (body == null || !body.contains("OTA")) {
                throw new RenException(ErrorCode.OTA_INTERFACE_FORMAT_ERROR);
            }
        } catch (Exception e) {
            throw new RenException(ErrorCode.OTA_INTERFACE_VALIDATION_FAILED);
        }
    }

    private void validateMcpUrl(String paramCode, String url) {
        if (!paramCode.equals(Constant.SERVER_MCP_ENDPOINT)) {
            return;
        }
        if (StringUtils.isBlank(url) || url.equals("null")) {
            return;
        }
        if (url.contains("localhost") || url.contains("127.0.0.1")) {
            throw new RenException(ErrorCode.MCP_URL_LOCALHOST);
        }
        if (!url.toLowerCase().contains("key")) {
            throw new RenException(ErrorCode.MCP_URL_INVALID);
        }

        try {
            // Gửi yêu cầu NHẬN
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            if (response.getStatusCode() != HttpStatus.OK) {
                throw new RenException(ErrorCode.MCP_INTERFACE_ACCESS_FAILED);
            }
            // Kiểm tra xem nội dung phản hồi có chứa thông tin liên quan đến mcp không
            String body = response.getBody();
            if (body == null || !body.contains("success")) {
                throw new RenException(ErrorCode.MCP_INTERFACE_FORMAT_ERROR);
            }
        } catch (Exception e) {
            throw new RenException(ErrorCode.MCP_INTERFACE_VALIDATION_FAILED);
        }
    }

    // Xác minh xem địa chỉ giao diện giọng nói có bình thường không
    private void validateVoicePrint(String paramCode, String url) {
        if (!paramCode.equals(Constant.SERVER_VOICE_PRINT)) {
            return;
        }
        if (StringUtils.isBlank(url) || url.equals("null")) {
            return;
        }
        if (url.contains("localhost") || url.contains("127.0.0.1")) {
            throw new RenException(ErrorCode.VOICEPRINT_URL_LOCALHOST);
        }
        if (!url.toLowerCase().contains("key")) {
            throw new RenException(ErrorCode.VOICEPRINT_URL_INVALID);
        }
        // Xác minh định dạng URL
        if (!url.toLowerCase().startsWith("http")) {
            throw new RenException(ErrorCode.VOICEPRINT_URL_PROTOCOL_ERROR);
        }
        try {
            // Gửi yêu cầu NHẬN
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            if (response.getStatusCode() != HttpStatus.OK) {
                throw new RenException(ErrorCode.VOICEPRINT_INTERFACE_ACCESS_FAILED);
            }
            // Kiểm tra nội dung phản hồi
            String body = response.getBody();
            if (body == null || !body.contains("healthy")) {
                throw new RenException(ErrorCode.VOICEPRINT_INTERFACE_FORMAT_ERROR);
            }
        } catch (Exception e) {
            throw new RenException(ErrorCode.VOICEPRINT_INTERFACE_VALIDATION_FAILED);
        }
    }

    // Xác minh độ dài và độ phức tạp của khóa mqtt
    private void validateMqttSecretLength(String paramCode, String secret) {
        if (!paramCode.equals(Constant.SERVER_MQTT_SECRET)) {
            return;
        }
        if (StringUtils.isBlank(secret) || secret.equals("null")) {
            throw new RenException(ErrorCode.MQTT_SECRET_EMPTY);
        }
        if (secret.length() < 8) {
            throw new RenException(ErrorCode.MQTT_SECRET_LENGTH_INSECURE);
        }
        // Kiểm tra xem nó có chứa cả chữ hoa và chữ thường không
        if (!secret.matches(".*[a-z].*") || !secret.matches(".*[A-Z].*")) {
            throw new RenException(ErrorCode.MQTT_SECRET_CHARACTER_INSECURE);
        }
        // Mật khẩu yếu không được phép
        String[] weakPasswords = { "test", "1234", "admin", "password", "qwerty", "xiaozhi" };
        for (String weakPassword : weakPasswords) {
            if (secret.toLowerCase().contains(weakPassword)) {
                throw new RenException(ErrorCode.MQTT_SECRET_WEAK_PASSWORD);
            }
        }
    }
}
