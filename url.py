import msvcrt
import os.path
import queue
import re
import sys
import time
import urllib2

# --- Constants ---
CELL_BLANK = 0  # Indicates that we know that a cell is blank, can't have any color there
CELL_EMPTY = -1 # Indicates that we don't know what's in a cell

STATUS_NOT_SURE = 0 # Element not yet determined
STATUS_SURE = 1 # Element determined: either we know what it is, or we know we can't know yet.


# --- Functions ---

# This function searches a particular puzzle row for possible solutions, given a list
# of hints and the total width of the puzzle. The given row with any newly determined
# elements is returned. Although "row" nomenclature is used, it is equally valid to use
# this for columns -- just transpose the hint and actual column to a row before inputting.
def search_possibilities(hints, actual_row, width):
   if len(hints) == 0:
      print "Error: zero length hints list!"
      return []
      
   # Begin recursion with no expansions (everything left shifted), no successes, and
   # a depth of 0. Then account for hints with consecutive ID's by starting the corresponding
   # expansions at 1.
   expansions = [ 1 if i > 0 and h[0] == hints[i-1][0] else 0 for i, h in enumerate(hints) ]
   base = [ (STATUS_NOT_SURE, actual_row[x]) for x in xrange(width) ]
   
   # Before recursing, perform one last check. If we definitely can't decide on any cells this
   # round, then don't even bother trying. In this instance, we limit only to empty rows and
   # check if the largest hint is longer than the remaining unused cells.
   should_search = True
   if sum(actual_row) == (CELL_EMPTY * width):
      largest_hint = max( [h[1] for h in hints] )
      num_unused_cells = width - calc_row_width(hints, expansions)
      if num_unused_cells < largest_hint:
         should_search = True
      else:
         should_search = False
         print "Skipping search, not enough hints."
         
   if should_search:
      search_possibilities_recursive(hints, expansions, actual_row, width, 0, base)

   return [x[1] for x in base]

   
# This function is a helper for search_possibilities() and should not be called directly.
# It's assumed that len(hints) and len(expansions) are equal!
# Output is base, which is a single row-length array of tuples. tuple[0] is a flag indicating
# if that element is determined yet (needed when merging in a new candidate row, and when
# all elements are determined we can stop searching for possibilities.
def search_possibilities_recursive(hints, expansions, actual_row, width, depth, base):
   # Make a full copy of the expansions list because we're going to modify it, and lists are passed
   # by reference so this would propagate up through the recursive calls (which we don't want).
   my_expansions = expansions[:]
   loop = True
   
   if should_quit_early():
      loop = False
   
   #dstring = " "*(depth*3) # depth indentation for prints
   while loop:
      # This is the typical break condition. If the hints + expansions we're trying are too big for the
      # row, then we need to bail on this combination. It just means we went too deep.
      current_width = calc_row_width(hints, my_expansions)
      #print dstring + "Current width: " + str(current_width)
      if current_width > width:
         #print dstring + "Too big!"
         break
      
      # Recursively try all possibilities
      if len(hints) - depth > 1: # Check here instead of in beginning of function to reduce pointless calls
         loop = search_possibilities_recursive(hints, my_expansions, actual_row, width, depth + 1, base)
      else:
         # Place the hints and expansions as they are right now and see if it's valid. Row is valid
         # if it fits and doesn't collide with anything already in place.
         test_row = actual_row[:] # Full copy
         test_row_idx = 0
         test_row_valid = True
         try: # Try / except used to break out of nested loop when placement attempt doesn't work
            for h, e in zip(hints, my_expansions):
               # First add the expansion. This ALWAYS comes before the corresponding hint.
               for i in xrange(e):
                  # Check to make sure we've not overrun
                  if test_row_idx >= width:
                     raise Exception
                  
                  # Check to make sure there's not something here. If there is and it doesn't match
                  # what we're trying to place bail out!
                  # Expansions can be validly placed over an empty or blank cell.
                  if test_row[test_row_idx] != CELL_EMPTY and test_row[test_row_idx] != CELL_BLANK:
                     raise Exception
                     
                  test_row[test_row_idx] = CELL_BLANK
                  test_row_idx = test_row_idx + 1
                  
               # Now add the hint.
               for i in xrange(h[1]):
                  # Check to make sure we've not overrun
                  if test_row_idx >= width:
                     raise Exception
                     
                  # Check to make sure there's not something here. If there is and it doesn't match
                  # what we're trying to place, bail out!
                  # Hints can ONLY be placed over an empty cell. If it's blank then we've
                  # determined that no hint ID can ever go there.
                  if test_row[test_row_idx] != CELL_EMPTY and test_row[test_row_idx] != h[0]:
                     raise Exception
                     
                  test_row[test_row_idx] = h[0]
                  test_row_idx = test_row_idx + 1
            
            # We've placed everything for this test, now make sure there's nothing left in the row.
            while test_row_idx < width:
               # If there's empty cells, mark them as blank so it's clear we intend it that way.
               # If it's already blank, leave it that way. If it's got something there, it's an
               # error so we need to bail (it has something that exceeds the hints).
               if test_row[test_row_idx] == CELL_EMPTY:
                  test_row[test_row_idx] = CELL_BLANK
               elif test_row[test_row_idx] == CELL_BLANK:
                  pass
               else:
                  raise Exception
               
               test_row_idx = test_row_idx + 1
                  
         except Exception:
            test_row_valid = False
         
         # If valid at this point, we have a complete candidate row.
         #print dstring + str(test_row)
         if test_row_valid == True:
            # Merge the base and candidate row.
            #print "   " + str(test_row)
            for i in xrange(width):
               if base[i][0] == STATUS_NOT_SURE:
                  if base[i][1] == CELL_EMPTY:
                     # The cell is currently empty, so if there's a better candidate go ahead and use it!
                     base[i] = (STATUS_NOT_SURE, test_row[i])
                  elif base[i][1] != test_row[i]:
                     # We've seen two different possibilities for this cell so we are sure we're not sure.
                     base[i] = (STATUS_SURE, CELL_EMPTY)
                  else:
                     # They're the same, so nothing changes.
                     pass
            
            # If we're sure of every element there's no point in continuing to search.
            if sum([x[0] for x in base]) == width: # Relies on STATUS_SURE == 1
               loop = False
               print "Stopping early, nothing new."
         else:
            #print dstring + "Doesn't fit!"
            pass
      
      # Increment the leftmost expansion, which corresponds to the current recursion depth.
      # Next pass through the loop we'll search all lower depths with this new value as a base.
      my_expansions[depth] = my_expansions[depth] + 1
      #print ""
      
   # Return true if looping should continue, false otherwise. Used to break out when there's
   # no more possibilities.
   return loop 

# This function calculates how wide the current row is based on an array of hints (tuples)
# and expansions. Typically will be used to check if we've exceeded the puzzle width.
def calc_row_width(hints, expansions):
   width = 0
   for h, e in zip(hints, expansions):
      width += h[1] + e
      
   return width


# This function checks if the grid is completed
def is_grid_complete(grid, left_hints, top_hints):
   # Check rows
   for row_idx in xrange(len(puzz_grid)):
      row = puzz_grid[row_idx]
      if not is_row_complete(row, left_hints[row_idx]):
         return False
      
   # Check columns
   for col_idx in xrange(len(puzz_grid[0])):
      col = [row[col_idx] for row in puzz_grid]
      if not is_row_complete(col, top_hints[col_idx]):
         return False
         
   # If we made it this far, the grid must be complete!
   return True


# This function determines if a row is completed. This logic can be applied to
# a column as well, the user just needs to transpose the column data to a row.
def is_row_complete(row, hints):
   if len(hints) == 0:
      return True
      
   # print "Checking:"
   # print "   row: " + str(row)
      
   col_idx = 0
   for hint in hints:
      id = hint[0]
      count = hint[1]
      # print "\n   hint: " + str(hint)
      
      hint_matched = False
      while hint_matched == False:
         if col_idx >= len(row):
            # Ran over the end of the row without finding a match for the hint
            # print "   Ran over length main loop"
            return False
            
         if row[col_idx] == id:
            # Found a cell that matches this hint, now make sure it matches the full hint
            # print "   Found beginning of hint " + str(hint)
            count = count - 1
            col_idx = col_idx + 1
            while count > 0:
               # print "      count: " + str(count)
               # print "      col_idx: " + str(col_idx)
               
               if col_idx >= len(row):
                  # Ran over the end of the row without finding the whole hint
                  # print "   Ran over length hint loop"
                  return False
                  
               if row[col_idx] != id:
                  # The hint has the correct ID but isn't the full length
                  # print "      Hint not long enough"
                  return False
               else:
                  count = count - 1
                  col_idx = col_idx + 1
            
            # If we made it this far, the hint was completely matched
            # print "   Hint matched!"
            hint_matched = True
            
         elif row[col_idx] == CELL_EMPTY or row[col_idx] == CELL_BLANK:
            # It's OK if there's a blank or empty cell before this hint is matched
            # print "   Found blank or empty at col_idx=" + str(col_idx)
            col_idx = col_idx + 1
         else:
            # We found a different ID than the hint was expecting. This probably means the row is wrong.
            # print "   ID doesn't match!"
            return False
            
   # If we made it through the whole row and each match and didn't have any issues then it must match!
   # print "Row is valid!"
   return True


# Determines if the program should quit early.
def should_quit_early():
   if msvcrt.kbhit():
      if msvcrt.getch() == 'q':
         msvcrt.ungetch('q')
         return True
   return False


# Deep copies a 2D grid
def copy_grid(grid):
   return [row[:] for row in grid]


# Checks if two 2D arrays are equal. Returns true if they are.
def grids_are_equal(a, b):
   for row_a, row_b in zip(a, b):
      for cell_a, cell_b in zip(row_a, row_b):
         if cell_a != cell_b:
            return False
   return True


# Convert all empty cells to blank
def empty_to_blank(row):
   for i in xrange(len(row)):
      if row[i] == CELL_EMPTY:
         row[i] = CELL_BLANK

# Store row of data back into the puzzle grid.
def save_row_into_grid(row, row_idx, grid):
   for i in xrange(len(row)):
      grid[row_idx][i] = row[i]


# Store column of data back into the puzzle grid.
def save_col_into_grid(col, col_idx, grid):
   for i in xrange(len(col)):
      grid[i][col_idx] = col[i]


# --- MAIN CODE BEGINS HERE ---
print ""

# System argument gives the puzzle ID, if none revert to a default
puzzle_id = 139714
if len(sys.argv) > 1:
   puzzle_id = int(sys.argv[1])

# Pull in the puzzle's solver page. This is the one that has the puzzle definition.
# If already exists on disk, just use that one. Otherwise grab from website and save to disk.
disk_file_name = "puzzles/griddler{0}.txt".format(puzzle_id)
web_html = ""
if os.path.isfile(disk_file_name):
   print "Reading HTML from disk."
   f = open(disk_file_name, "r")
   web_html = f.read()
   f.close()
else:
   print "Reading HTML from website."
   web_url_base = 'http://www.griddlers.net/griddlers?p_p_id=griddlers_WAR_puzzles&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=html&p_p_cacheability=cacheLevelPage&p_p_col_id=column-2&p_p_col_count=1&_griddlers_WAR_puzzles_id={0}&_griddlers_WAR_puzzles_view=detail'
   web_url = web_url_base.format(puzzle_id) # Add the puzzle ID into the url
   web_file = urllib2.urlopen(web_url)
   web_html = web_file.read()
   
   print "Writing HTML to disk."
   f = open(disk_file_name, "w")
   f.write(web_html)
   f.close()
print "Page data retrieved."


# Extract puzzle details

# Puzzle width
result = re.search('var pwidth = ([0-9]+)', web_html)
puzz_width = int(result.group(1))
print "Puzzle width: " + str(puzz_width)

# Puzzle height
result = re.search('var pheight = ([0-9]+)', web_html)
puzz_height = int(result.group(1))
print "Puzzle height: " + str(puzz_height)

# Puzzle horizontal (left) codes
puzz_left_hints = []
for result in re.finditer('leftCodes\[[0-9]+\]=\"(.*)\";', web_html):
   left_hint_list = []
   for r in result.group(1).split(','):
      left_hint = re.search('([0-9]+):([0-9]+)', r)
      if left_hint:
         palette_id = int(left_hint.group(1))
         count = int(left_hint.group(2))
         left_hint_list.append( (palette_id, count) )
   puzz_left_hints.append(left_hint_list)

# Puzzle vertical (top) codes
puzz_top_hints = []
for result in re.finditer('topCodes\[[0-9]+\]=\"(.*)\";', web_html):
   top_hint_list = []
   for r in result.group(1).split(','):
      top_hint = re.search('([0-9]+):([0-9]+)', r)
      if top_hint:
         palette_id = int(top_hint.group(1))
         count = int(top_hint.group(2))
         top_hint_list.append( (palette_id, count) )
   puzz_top_hints.append(top_hint_list)


# Create puzzle grid
puzz_grid = [[CELL_EMPTY for x in xrange(puzz_width)] for x in xrange(puzz_height)]
last_puzz_grid = copy_grid(puzz_grid)

# Search possibilities
puzz_is_complete = False
quit_early = False
begin_time = time.clock()
while True:
   for row_idx in xrange(len(puzz_grid)):
      # Get row and hints for this pass
      print "Row " + str(row_idx)
      row = puzz_grid[row_idx]
      hints = puzz_left_hints[row_idx]
      
      # Check if row is already valid before searching possibilities. If it's valid,
      # it may still have empty cells so convert those to blanks and save that back
      # into the grid.
      if is_row_complete(row, hints):
         empty_to_blank(row)
         save_row_into_grid(row, row_idx, puzz_grid)
         print "   already complete!"
         continue
      
      # Try to solve as much of this row as possible
      row = search_possibilities(hints, row, puzz_width)
      if should_quit_early():
         quit_early = True
         break
      print "\nCurrent: "
      print row
      
      # Check again if the row is valid, since we may have just completed it.
      # We do this now to pre-emptively fill in any empty cells with blank ones.
      if is_row_complete(row, hints):
         empty_to_blank(row)
         print "   just completed!"
      
      # Save row of data back into the puzzle grid
      save_row_into_grid(row, row_idx, puzz_grid)
      print ""
      #raw_input("Press Enter to continue...")
   
   if should_quit_early():
      quit_early = True
      break
      
      
   for col_idx in xrange(len(puzz_grid[0])):
      # Get column and hints for this pass
      print "Col " + str(col_idx)
      col = [row[col_idx] for row in puzz_grid]
      hints = puzz_top_hints[col_idx]
      
      # Check if col is already valid before searching possibilities. If it's valid,
      # it may still have empty cells so convert those to blanks and save that back
      # into the grid.
      if is_row_complete(col, hints):
         empty_to_blank(col)
         save_col_into_grid(col, col_idx, puzz_grid)
         print "   already complete!"
         continue
      
      # Try to solve as much of this column as possible
      col = search_possibilities(hints, col, puzz_height)
      if should_quit_early():
         quit_early = True
         break
      print "\nCurrent:"
      print col
      
      # Check again if the column is valid, since we may have just completed it.
      # We do this now to pre-emptively fill in any empty cells with blank ones.
      if is_row_complete(col, hints):
         empty_to_blank(col)
         print "   just completed!"
      
      # Save column of data back into the puzzle grid.
      save_col_into_grid(col, col_idx, puzz_grid)
      
      print ""
      #raw_input("Press Enter to continue...")
      
   if should_quit_early():
      quit_early = True
      break
      
      
   # Check if whole grid is valid now
   if is_grid_complete(puzz_grid, puzz_left_hints, puzz_top_hints):
      print "\nGrid is complete!!"
      puzz_is_complete = True
      break
   
   # Check if grid has changed -- if not, we can't solve it!
   if grids_are_equal(puzz_grid, last_puzz_grid):
      print "\nGrid is unable to be solved! :("
      puzz_is_complete = False
      break
      
   print ""
   for row in puzz_grid:
      print row
   
   print "Grid not complete yet, iterating again...\n"
   last_puzz_grid = copy_grid(puzz_grid) # Make a copy for comparison after next iteration
   #raw_input("Press Enter to continue...\n")


# We're done solving! Now get the solve time and dump data to disk.
end_time = time.clock()
solve_time = end_time - begin_time
solve_h = int(solve_time / 60 / 60)
solve_m = int((solve_time - (solve_h * 60 * 60)) / 60)
solve_s = int(solve_time - (solve_m * 60))
solve_time_str = "Solve time: " + str(solve_time) + " ({0}h {1}m {2}s)".format(solve_h, solve_m, solve_s)

print "Final grid:"
for row in puzz_grid:
   print row
print "Time: " + solve_time_str

# File name suffix for easy ID if the file is solved or not
suffix = ""
if puzz_is_complete:
   suffix = "solved"    # Puzzle is complete!
elif quit_early:
   suffix = "quit"      # User quit the puzzle while solving
else:
   suffix = "unsolved"  # Unable to be solved!

solved_file_name = "{0}-{1}.txt".format(disk_file_name, suffix)
fout = open(solved_file_name, "w")
fout.write(solve_time_str + "\n")
for row in puzz_grid:
   row_str = ""
   for cell in row:
      row_str = row_str + str(cell) + " "
   row_str = row_str + "\n"
   fout.write(row_str)
fout.close()
#raw_input("Press Enter to continue...")

# - Could have a speedup where if the row is empty and the sum of the components isn't long enough,
#   just skip the row and return all empties.
# - I should really create a custom exception so that regular ones aren't getting caught in the search loop
# - Create a queueing system for which rows / cols to look through. Initially add one or more that are
#   very long. Then when a cell changes, add that row or col to the queue to be checked. If the queue is
#   empty then revert to scanning through row x col.
# - GRAPHICS!!
# - Maybe there's a way to start the hints / expansions at a certain point, based on what's already out?
#   I guess if you knew everything starting from the left or right you could say definitively whole hints.
# - Could investigate using regex matching algorithms to match hints with rows.