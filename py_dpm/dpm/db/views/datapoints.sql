CREATE OR ALTER VIEW datapoints AS
SELECT distinct tvc.CellCode AS cell_code,
       tv.Code                                       AS table_code,
       hvr.Code                                      AS row_code,
       hvc.Code                                      AS column_code,
       hvs.Code                                      AS sheet_code,
       vv.VariableID                                 AS variable_id,
       dt.Code                                       AS data_type,
       tv.TableVID                                   AS table_vid,

       p.PropertyID                                  AS property_id,
       mv.StartReleaseID                             AS start_release,
       mv.EndReleaseID                               AS end_release,
       tvc.CellID                                    AS cell_id,
       vv.ContextID                                  AS context_id,
       vv.VariableVID                                AS variable_vid

FROM dbo.TableVersionCell AS tvc

         INNER JOIN dbo.TableVersion AS tv
                    ON tvc.TableVID = tv.TableVID AND tvc.IsVoid = 0
        INNER JOIN dbo.ModuleVersionComposition mvc on tv.TableVID = mvc.TableVID
        inner join dbo.ModuleVersion mv on mvc.ModuleVID = mv.ModuleVID

         LEFT OUTER JOIN dbo.VariableVersion AS vv
                    ON tvc.VariableVID = vv.VariableVID

         LEFT OUTER JOIN dbo.Property AS p ON vv.PropertyID = p.PropertyID

         LEFT OUTER JOIN dbo.DataType AS dt ON p.DataTypeID = dt.DataTypeID

         INNER JOIN dbo.Cell AS c ON tvc.CellID = c.CellID

         LEFT OUTER JOIN

     (SELECT hv.HeaderVID, hv.HeaderID, hv.Code, hv.EndReleaseID, tvh.TableVID

      FROM HeaderVersion hv

               INNER JOIN TableVersionHeader tvh
                          ON tvh.HeaderVID = hv.HeaderVID) hvr
     ON hvr.HeaderID = c.RowID AND hvr.EndReleaseID IS NULL AND
        tv.TableVID = hvr.TableVID

         LEFT OUTER JOIN

     (SELECT hv.HeaderVID, hv.HeaderID, hv.Code, hv.EndReleaseID, tvh.TableVID

      FROM HeaderVersion hv

               INNER JOIN TableVersionHeader tvh
                          ON tvh.HeaderVID = hv.HeaderVID) hvc
     ON hvc.HeaderID = c.ColumnID AND hvc.EndReleaseID IS NULL AND
        tv.TableVID = hvc.TableVID

         LEFT OUTER JOIN

     (SELECT hv.HeaderVID, hv.HeaderID, hv.Code, hv.EndReleaseID, tvh.TableVID

      FROM HeaderVersion hv

               INNER JOIN TableVersionHeader tvh
                          ON tvh.HeaderVID = hv.HeaderVID) hvs
     ON hvs.HeaderID = c.SheetID AND hvs.EndReleaseID IS NULL AND
        tv.TableVID = hvs.TableVID