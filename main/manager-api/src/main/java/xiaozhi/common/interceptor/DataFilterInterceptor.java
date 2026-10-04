package xiaozhi.common.interceptor;

import java.util.Map;

import org.apache.ibatis.executor.Executor;
import org.apache.ibatis.mapping.BoundSql;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.session.ResultHandler;
import org.apache.ibatis.session.RowBounds;

import com.baomidou.mybatisplus.core.toolkit.PluginUtils;
import com.baomidou.mybatisplus.extension.plugins.inner.InnerInterceptor;

import cn.hutool.core.util.StrUtil;
import net.sf.jsqlparser.JSQLParserException;
import net.sf.jsqlparser.expression.Expression;
import net.sf.jsqlparser.expression.StringValue;
import net.sf.jsqlparser.expression.operators.conditional.AndExpression;
import net.sf.jsqlparser.parser.CCJSqlParserUtil;
import net.sf.jsqlparser.statement.select.PlainSelect;
import net.sf.jsqlparser.statement.select.Select;

/**
 * Lọc dữ liệu
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
public class DataFilterInterceptor implements InnerInterceptor {

    @SuppressWarnings("rawtypes")
    @Override
    public void beforeQuery(Executor executor, MappedStatement ms, Object parameter, RowBounds rowBounds,
            ResultHandler resultHandler, BoundSql boundSql) {
        DataScope scope = getDataScope(parameter);
        // Không lọc dữ liệu
        if (scope == null || StrUtil.isBlank(scope.getSqlFilter())) {
            return;
        }

        // Nối SQL mới
        String buildSql = getSelect(boundSql.getSql(), scope);

        // Viết lại SQL
        PluginUtils.mpBoundSql(boundSql).sql(buildSql);
    }

    private DataScope getDataScope(Object parameter) {
        if (parameter == null) {
            return null;
        }

        // Xác định xem có đối tượng DataScope trong tham số không
        if (parameter instanceof Map) {
            Map<?, ?> parameterMap = (Map<?, ?>) parameter;
            for (Map.Entry<?, ?> entry : parameterMap.entrySet()) {
                if (entry.getValue() != null && entry.getValue() instanceof DataScope) {
                    return (DataScope) entry.getValue();
                }
            }
        } else if (parameter instanceof DataScope) {
            return (DataScope) parameter;
        }

        return null;
    }

    private String getSelect(String buildSql, DataScope scope) {
        try {
            Select select = (Select) CCJSqlParserUtil.parse(buildSql);
            PlainSelect plainSelect = select.getPlainSelect();

            Expression expression = plainSelect.getWhere();
            if (expression == null) {
                plainSelect.setWhere(new StringValue(scope.getSqlFilter()));
            } else {
                AndExpression andExpression = new AndExpression(expression, new StringValue(scope.getSqlFilter()));
                plainSelect.setWhere(andExpression);
            }

            return select.toString().replaceAll("'", "");
        } catch (JSQLParserException e) {
            return buildSql;
        }
    }
}
