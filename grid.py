import msvcrt
#from pprint import pprint


class Grid:
   
   CELL_BLANK = ' '  # Indicates that we know that a cell is blank, can't have any color there
   CELL_EMPTY = '-' # Indicates that we don't know what's in a cell
   
   STATUS_NOT_SURE = 0 # Element not yet determined
   STATUS_SURE = 1 # Element determined: either we know what it is, or we know we can't know yet.
   
   def __init__(self, size_x, size_y, hints_col, hints_row):
      self.grid = {} # Access as grid[x, y]
      for x in xrange(size_x):
         for y in xrange(size_y):
            self.grid[x, y] = Grid.CELL_EMPTY
      
      self.solved_cols = [False for x in xrange(size_x)]
      self.solved_rows = [False for y in xrange(size_y)]
      
      self.size_x = size_x
      self.size_y = size_y
      self.hints_col = hints_col
      self.hints_row = hints_row
   
   
   def __repr__(self, ):
      row_str = []
      for y in xrange(self.size_y):
         row = self.get_row(y)
         row_str.append(' '.join(map(str, row)))
      return '\n'.join(row_str) + '\n'
   
   
   def solve(self):
      puzz_is_complete = False
      
      while puzz_is_complete is False:
         for x in xrange(self.size_x):
            # Check if the col has already been solved before trying to solve it
            if not self.is_col_solved(x):
               # Allow the user to quit early
               if self.should_quit_early():
                  return
               
               # Get line and hints for this pass
               line = self.get_col(x)
               hints = self.hints_col[x]
               
               # Solve as much of this line as possible
               result = self.solve_line(line, hints)
               
               # The line may have just been completed, if so convert all empties to blanks
               # to improve results / efficiency on other lines
               self.is_col_solved(x)
               
               # Save result back into the puzzle grid
               self.set_col(x, result)
         
         for y in xrange(self.size_y):
            # Check if the row has already been solved before trying to solve it
            if not self.is_row_solved(y):
               # Allow the user to quit early
               if self.should_quit_early():
                  return
               
               # Get line and hints for this pass
               line = self.get_row(y)
               hints = self.hints_row[y]
               
               # Solve as much of this line as possible
               line = self.solve_line(line, hints)
               
               # The line may have just been completed, if so convert all empties to blanks
               # to improve results / efficiency on other lines
               self.is_row_solved(y)
               
               # Save line of data back into the puzzle grid
               self.set_row(y, line)
         
         # Check if whole grid is solved now
         if self.is_solved():
            puzz_is_complete = True
            break
         
         # Check if grid has changed -- if not, we can't solve it!
         #if grids_are_equal(puzz_grid, last_puzz_grid):
            #print "\nGrid is unable to be solved! :("
            #puzz_is_complete = False
            #break
         
         print 'Current grid:'
         print self
         
         #print "Grid not complete yet, iterating again...\n"
         #last_puzz_grid = copy_grid(puzz_grid) # Make a copy for comparison after next iteration
         #raw_input("Press Enter to continue...\n")
   
   
   def solve_line(self, line, hints):
      line_len = len(line)
      
      # Begin recursion with no expansions (everything left shifted), no successes, and
      # a depth of 0. Then account for hints with consecutive ID's by starting the corresponding
      # expansions at 1.
      expansions = [ 1 if i > 0 and h[0] == hints[i-1][0] else 0 for i, h in enumerate(hints) ]
      status = [Grid.STATUS_NOT_SURE for i in xrange(line_len)]
      result = line[:]
      
      # Before recursing, perform one last check. If we definitely can't decide on any cells this
      # round, then don't even bother trying. In this instance, we limit only to empty rows and
      # check if the largest hint is longer than the remaining unused cells.
      should_search = True
      if line == [Grid.CELL_EMPTY] * line_len:
         hints_count_list = [count for id, count in hints]
         expanded_length = sum(expansions) + sum(hints_count_list)
         num_unused_cells = line_len - expanded_length
         
         if num_unused_cells >= max(hints_count_list):
            should_search = False
            #print "Skipping search, not enough hints."
      
      if should_search:
         self.solve_line_recursive(line, hints, expansions, 0, status, result)
      
      return result
   
   
   # This function is a helper for search_possibilities() and should not be called directly.
   # It's assumed that len(hints) and len(expansions) are equal!
   # Output is result, which is a single line-length list of values. status is a flag indicating
   # if the corresponding result element is determined yet (needed when merging in a new
   # candidate line, and when all elements are determined we can stop searching for possibilities.
   # Return True if looping should continue, False otherwise. Used to break out when there's
   # no more possibilities.
   def solve_line_recursive(self, line, hints, expansions, depth, status, result):
      # Make a full copy of the expansions list because we're going to modify it, and we don't
      # want changes to propagate up through the recursive calls.
      hints_count_list = [count for id, count in hints]
      my_expansion = expansions[depth] # Push expansion value, should always be the original base expansion of either 0 or 1
      line_len = len(line)
      
      loop = True
      if self.should_quit_early():
         loop = False
      
      #dstring = ' '*3*depth # depth indentation for prints
      while loop:
         # This is the typical break condition. If the hints + expansions we're trying are too big for the
         # line, then we need to bail on this combination. It just means we went too deep.
         expanded_length = sum(expansions) + sum(hints_count_list)
         #print dstring + "Current length:", expanded_length
         if expanded_length > line_len:
            #print dstring + "Too big!"
            break
         
         # Recursively try all possibilities
         if len(hints) - depth > 1: # Check here instead of in beginning of function to reduce pointless calls
            loop = self.solve_line_recursive(line, hints, expansions, depth + 1, status, result)
         else:
            # Place the hints and expansions as they are right now and see if it's valid. Line is valid
            # if it fits and doesn't collide with anything already in place.
            test_line = line[:]
            test_line_idx = 0
            test_line_valid = True
            try: # Try / except used to break out of nested loop when placement attempt doesn't work
               # Check to make sure there's not something here. If there is and it doesn't match
               # what we're trying to place, bail out!
               def try_set(line, idx, value):
                  if line[idx] == Grid.CELL_EMPTY:
                     line[idx] = value
                  elif line[idx] == value:
                     pass
                  else:
                     raise Exception
               
               # Place each expansion and hint
               for (hint_id, hint_count), e in zip(hints, expansions):
                  # First add the expansion. This ALWAYS comes before the corresponding hint.
                  for i in xrange(e):
                     try_set(test_line, test_line_idx + i, Grid.CELL_BLANK)
                  test_line_idx += e
                  
                  # Now add the hint.
                  for i in xrange(hint_count):
                     try_set(test_line, test_line_idx + i, hint_id)
                  test_line_idx += hint_count
               
               # We've placed everything for this test, now make sure there's nothing left in the line.
               # Mark the remaining cells as blank, if there's something else there then that's an error.
               for i in xrange(line_len - test_line_idx):
                  try_set(test_line, test_line_idx + i, Grid.CELL_BLANK)
               
            except (Exception, IndexError):
               test_line_valid = False
            
            # If valid at this point, we have a complete candidate line.
            #print dstring + str(test_line)
            if test_line_valid is True:
               # Merge the result and candidate line.
               #print ' '*3 + str(test_line)
               for i, value in enumerate(result):
                  if status[i] == Grid.STATUS_NOT_SURE:
                     if value == Grid.CELL_EMPTY:
                        # The cell is currently empty, so if there's a better candidate go ahead and use it!
                        status[i] = Grid.STATUS_NOT_SURE
                        result[i] = test_line[i]
                     elif value != test_line[i]:
                        # We've seen two different possibilities for this cell so we are sure we don't know what it is.
                        status[i] = Grid.STATUS_SURE
                        result[i] = Grid.CELL_EMPTY
                     else:
                        # They're the same, so nothing changes.
                        pass
               
               # If we're sure of every element there's no point in continuing to search.
               if status == [Grid.STATUS_SURE] * line_len:
                  loop = False
                  print "Stopping early, nothing new."
               
            else:
               #print dstring + "Doesn't fit!"
               pass
         
         # Increment the leftmost expansion, which corresponds to the current recursion depth.
         # Next pass through the loop we'll search all lower depths with this new value as a base.
         expansions[depth] += 1
         #print ""
      
      expansions[depth] = my_expansion # Pop expansion value
      
      return loop 
   
   
   def is_solved(self):
      # Check columns (iterate in x direction)
      for x in xrange(self.size_x):
         if not self.solved_cols[x]:
            return False
      
      # Check rows (iterate in y direction)
      for y in xrange(self.size_y):
         if not self.solved_rows[y]:
            return False
      
      # If we made it this far, the grid must be complete!
      return True
   
   
   def is_line_solved(self, line, hints):
      # print "Checking:"
      # print "   line:", line
      
      try:
         idx = 0 # todo: make this into an iterator
         for hint in hints:
            id, count = hint
            # print "\n   hint:", hint
            
            hint_matched = False
            while hint_matched is False:
               if line[idx] == id:
                  # Found a cell that matches this hint, now make sure it matches the full hint
                  # print "   Found beginning of hint", hint
                  count -= 1
                  idx   += 1
                  
                  while count > 0:
                     # print "      count:", count
                     # print "      idx:", idx
                     
                     if line[idx] != id:
                        # The hint has the correct ID but isn't the full length
                        # print "      Hint not long enough"
                        return False
                        
                     else:
                        count -= 1
                        idx   += 1
                  
                  # If we made it this far, the hint was completely matched
                  # print "   Hint matched!"
                  hint_matched = True
                  
               elif line[idx] == Grid.CELL_BLANK:
                  # It's OK if there's a blank or empty cell before this hint is matched
                  # print "   Found blank or empty at idx =", idx
                  idx += 1
                  
               else:
                  # We found a different ID than the hint was expecting. This means the line is wrong.
                  # print "   ID doesn't match!"
                  return False
               
      except IndexError:
         # Ran over the end of the line without finding a match for the hint
         # print "   Ran over length main loop"
         return False
      
      # If we made it through the whole line and each hint and didn't have any issues then it must match!
      # print "Line is valid!"
      return True
   
   
   def is_col_solved(self, x):
      if self.solved_cols[x] is False:
         line = self.get_col(x)
         hints = self.hints_col[x]
         
         if self.is_line_solved(line, hints) is True:
            self.solved_cols[x] = True
            self.empty_to_blank(line)
            self.set_col(x, line)
      
      return self.solved_cols[x]
   
   
   def is_row_solved(self, y):
      if self.solved_rows[y] is False:
         line = self.get_row(y)
         hints = self.hints_row[y]
         
         if self.is_line_solved(line, hints) is True:
            self.solved_rows[y] = True
            self.empty_to_blank(line)
            self.set_row(y, line)
      
      return self.solved_rows[y]
   
   
   def get_col(self, x):
      return [self.grid[x, y] for y in xrange(self.size_y)]
   
   
   def get_row(self, y):
      return [self.grid[x, y] for x in xrange(self.size_x)]
   
   
   def set_col(self, x, data):
      for y in xrange(self.size_y):
         self.grid[x, y] = data[y]
   
   
   def set_row(self, y, data):
      for x in xrange(self.size_x):
         self.grid[x, y] = data[x]
   
   
   # Convert all empty cells to blank
   def empty_to_blank(self, line):
      for i in xrange(len(line)):
         if line[i] == Grid.CELL_EMPTY:
            line[i] = Grid.CELL_BLANK
   
   
   def should_quit_early(self): # todo: something with this. ugly.
      if msvcrt.kbhit():
         if msvcrt.getch() == 'q':
            msvcrt.ungetch('q')
            return True
      return False
   